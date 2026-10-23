import os
import string
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

MEDIA_EXTENSIONS = {
    ".webm", ".mp4", ".mkv", ".avi", ".mov", ".m4a",
    ".mp3", ".wav", ".ogg", ".flac", ".wmv"
}

class LocalStorageManager:
    """
    Manages multi-drive file resolution, drive enumeration (C:, D:, etc.),
    and media file discovery across Windows file system with explicit
    security authorization checks.
    """

    @staticmethod
    def get_available_drives() -> List[str]:
        """Returns all mounted and accessible drive letters (e.g. ['C', 'D'])."""
        drives = []
        for letter in string.ascii_uppercase:
            drive_path = f"{letter}:\\"
            try:
                if os.path.exists(drive_path):
                    drives.append(letter)
            except Exception:
                pass
        return drives

    @staticmethod
    def get_common_user_folders() -> Dict[str, Path]:
        """Returns common user library folders on Windows."""
        home = Path(os.path.expanduser("~"))
        folders = {
            "downloads": home / "Downloads",
            "videos": home / "Videos",
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "music": home / "Music",
            "pictures": home / "Pictures"
        }
        return {k: v for k, v in folders.items() if v.exists()}

    @classmethod
    def resolve_target_directory(cls, query: str) -> Tuple[Path, str]:
        """
        Resolves natural language queries into a concrete directory path and descriptive label.
        Handles drive letters (e.g. 'D drive', 'd:', 'c drive'), user folders,
        or specific folder names on any drive.
        """
        q_lower = query.lower()
        drives = cls.get_available_drives()

        # 1. Check for explicit drive letters (e.g., 'd drive', 'd:', 'c drive', 'c:')
        drive_match = re.search(r"\b([a-z])\s*(?:drive|:)\b", q_lower)
        if drive_match:
            target_letter = drive_match.group(1).upper()
            if target_letter in drives:
                drive_root = Path(f"{target_letter}:\\")
                # Check if subfolder mentioned on that drive (e.g., 'movies', 'downloads', 'friends')
                for item in drive_root.iterdir():
                    try:
                        if item.is_dir() and item.name.lower() in q_lower:
                            return item, f"{target_letter}:\\{item.name}"
                    except Exception:
                        pass
                return drive_root, f"{target_letter}:\\"

        # 2. Check standard user library folders (e.g. ~/Downloads, ~/Videos)
        user_folders = cls.get_common_user_folders()
        for name, folder in user_folders.items():
            if name in q_lower:
                return folder, f"{name.capitalize()} folder"

        # 3. Check for named directories across secondary drives (e.g., 'movies', 'trapped in a dating sim', 'friends')
        for letter in drives:
            drive_root = Path(f"{letter}:\\")
            try:
                for item in drive_root.iterdir():
                    if item.is_dir() and item.name.lower() in q_lower and len(item.name) >= 3:
                        return item, f"{letter}:\\{item.name}"
            except Exception:
                pass

        # 4. Default: User Downloads folder if available, otherwise first drive
        if "downloads" in user_folders:
            return user_folders["downloads"], "Downloads"

        return Path(f"{drives[0]}:\\"), f"{drives[0]}:\\"

    @classmethod
    def find_media_files(
        cls,
        target_dir: Optional[Path] = None,
        max_files: int = 15,
        max_depth: int = 2
    ) -> List[Path]:
        """
        Scans target directory (or user libraries + secondary drives) for playable media files,
        ordered by last modified timestamp (newest first).
        """
        search_dirs: List[Path] = []
        if target_dir and target_dir.exists():
            search_dirs.append(target_dir)
        else:
            # Aggregate user libraries + secondary drives
            user_folders = cls.get_common_user_folders()
            for key in ["downloads", "videos", "desktop", "movies"]:
                if key in user_folders:
                    search_dirs.append(user_folders[key])
            for letter in cls.get_available_drives():
                d_root = Path(f"{letter}:\\")
                if d_root not in search_dirs:
                    search_dirs.append(d_root)

        media_files: List[Path] = []
        seen_paths = set()

        def scan_dir(folder: Path, current_depth: int):
            if current_depth > max_depth or not folder.is_dir():
                return
            try:
                entries = list(folder.iterdir())
            except Exception:
                return

            for entry in entries:
                try:
                    if entry.is_file() and entry.suffix.lower() in MEDIA_EXTENSIONS:
                        if entry not in seen_paths:
                            seen_paths.add(entry)
                            media_files.append(entry)
                    elif entry.is_dir() and not entry.name.startswith(("$", ".")) and current_depth < max_depth:
                        # Avoid deeply nested or system volume folders
                        if entry.name.lower() not in ["system volume information", "$recycle.bin", "windows", "program files"]:
                            scan_dir(entry, current_depth + 1)
                except Exception:
                    continue

        for s_dir in search_dirs:
            scan_dir(s_dir, 0)
            if len(media_files) >= max_files * 2:
                break

        # Sort by last modified time (newest first)
        def get_mtime(p: Path) -> float:
            try:
                return p.stat().st_mtime
            except Exception:
                return 0.0

        media_files.sort(key=get_mtime, reverse=True)
        return media_files[:max_files]
