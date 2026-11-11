/**
 * Persistent IndexedDB store + directory scanner for Chrome File System Access API
 * (`showDirectoryPicker` / `FileSystemDirectoryHandle`).
 *
 * Allows one-time folder authorization ("Allow on every visit") on non-restricted
 * local folders (e.g., Videos, Music, D:\Movies, or Downloads\Media) so VECTOR can
 * automatically scan and play matching/latest media without per-file prompts.
 */

const DB_NAME = 'vector_local_storage';
const DB_VERSION = 1;
const STORE_NAME = 'handles';
const PRIMARY_FOLDER_KEY = 'primary_media_folder';

export const MEDIA_FILE_REGEX = /\.(mp4|mkv|webm|mov|avi|m4v|mp3|m4a|wav|ogg|flac|aac|opus)$/i;
export const AUDIO_FILE_REGEX = /\.(mp3|m4a|wav|ogg|flac|aac|opus)$/i;

export type FolderPermissionState = 'granted' | 'prompt' | 'denied';

export interface SavedFolderRecord {
  handle: FileSystemDirectoryHandle;
  name: string;
  savedAt: number;
}

const STOPWORDS = new Set([
  'play',
  'open',
  'start',
  'watch',
  'listen',
  'find',
  'show',
  'run',
  'the',
  'a',
  'an',
  'latest',
  'newest',
  'recent',
  'last',
  'first',
  'top',
  'any',
  'some',
  'media',
  'video',
  'videos',
  'audio',
  'music',
  'song',
  'songs',
  'movie',
  'movies',
  'clip',
  'clips',
  'file',
  'files',
  'from',
  'of',
  'in',
  'on',
  'at',
  'to',
  'my',
  'local',
  'pc',
  'computer',
  'folder',
  'directory',
  'downloads',
  'download',
  'desktop',
  'documents',
  'drive',
  'chrome',
  'tab',
  'window',
  'please',
]);

export function isDirectoryPickerSupported(): boolean {
  return typeof window !== 'undefined' && typeof (window as any).showDirectoryPicker === 'function';
}

function openHandlesDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB unavailable'));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('Failed to open IndexedDB'));
  });
}

export async function saveMediaFolderHandle(handle: FileSystemDirectoryHandle): Promise<void> {
  try {
    const db = await openHandlesDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const record: SavedFolderRecord = {
        handle,
        name: handle.name || 'Media Folder',
        savedAt: Date.now(),
      };
      store.put(record, PRIMARY_FOLDER_KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error('Failed to persist folder handle'));
    });
    db.close();
  } catch {
    // Ignore storage failures (e.g., private browsing mode)
  }
}

export async function getSavedMediaFolder(): Promise<SavedFolderRecord | null> {
  try {
    const db = await openHandlesDb();
    const record = await new Promise<SavedFolderRecord | null>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(PRIMARY_FOLDER_KEY);
      req.onsuccess = () => resolve((req.result as SavedFolderRecord) || null);
      req.onerror = () => reject(req.error || new Error('Failed to load folder handle'));
    });
    db.close();
    if (!record || !record.handle) return null;
    return record;
  } catch {
    return null;
  }
}

export async function clearSavedMediaFolder(): Promise<void> {
  try {
    const db = await openHandlesDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).delete(PRIMARY_FOLDER_KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error('Failed to delete folder handle'));
    });
    db.close();
  } catch {
    // Ignore cleanup errors
  }
}

export async function queryFolderPermission(
  handle: FileSystemDirectoryHandle
): Promise<FolderPermissionState> {
  try {
    const fn = (handle as any).queryPermission;
    if (typeof fn !== 'function') return 'prompt';
    const res = await fn.call(handle, { mode: 'read' });
    if (res === 'granted' || res === 'denied') return res;
    return 'prompt';
  } catch {
    return 'prompt';
  }
}

export async function requestFolderPermission(
  handle: FileSystemDirectoryHandle
): Promise<FolderPermissionState> {
  try {
    const fn = (handle as any).requestPermission;
    if (typeof fn !== 'function') return 'denied';
    const res = await fn.call(handle, { mode: 'read' });
    if (res === 'granted' || res === 'denied') return res;
    return 'prompt';
  } catch {
    return 'denied';
  }
}

export async function scanDirectoryMediaFiles(
  dirHandle: FileSystemDirectoryHandle,
  maxFiles = 250,
  maxDepth = 2
): Promise<File[]> {
  const results: File[] = [];

  const walk = async (handle: FileSystemDirectoryHandle, depth: number) => {
    if (results.length >= maxFiles) return;
    try {
      const iterator = (handle as any).values?.() as AsyncIterable<FileSystemHandle> | undefined;
      if (!iterator) return;
      for await (const entry of iterator) {
        if (results.length >= maxFiles) break;
        if (entry.name.startsWith('.') || entry.name.startsWith('$')) continue;
        if (entry.kind === 'file') {
          if (!MEDIA_FILE_REGEX.test(entry.name)) continue;
          try {
            const file = await (entry as FileSystemFileHandle).getFile();
            if (file.size > 0) {
              results.push(file);
            }
          } catch {
            // Skip unreadable entry
          }
        } else if (entry.kind === 'directory' && depth < maxDepth) {
          await walk(entry as FileSystemDirectoryHandle, depth + 1);
        }
      }
    } catch {
      // Ignore permission/read errors on individual subdirectories
    }
  };

  await walk(dirHandle, 0);
  return results;
}

export function isLocalMediaTask(task: string): boolean {
  const t = (task || '').toLowerCase();
  if (!t || /\byoutube\b/i.test(t) || /\binvoice\b|\bprocurement\b|\brequisition\b|\bgithub\b/i.test(t)) {
    return false;
  }
  const mentionsLocalContainer =
    /\b(downloads?|folder|directory|local\s*(?:media|video|audio|file)|my\s+(?:(?:latest|newest|recent|first|top)\s+)?(?:videos?|music|media|files?)|authorized\s*folder|movies?\s*folder|d:|c:)\b/i.test(
      t
    ) || /\bfrom\s+(?:videos?|music|movies?|downloads?|media|folder)\b/i.test(t);
  const mentionsMedia = /\b(play|watch|listen|open|media|video|videos|audio|music|song|songs|movie|movies|mp4|mkv|webm|mp3)\b/i.test(
    t
  );
  return mentionsLocalContainer && mentionsMedia;
}

export function rankMediaFilesForTask(files: File[], task: string): File[] {
  const media = files.filter(
    (f) => MEDIA_FILE_REGEX.test(f.name) || f.type.startsWith('video/') || f.type.startsWith('audio/')
  );
  const tokens = (task || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((tok) => tok.length >= 2 && !STOPWORDS.has(tok));

  return [...media].sort((a, b) => {
    if (tokens.length > 0) {
      const aStem = a.name.toLowerCase().replace(/\.[^.]+$/, '');
      const bStem = b.name.toLowerCase().replace(/\.[^.]+$/, '');
      const aScore = tokens.reduce((acc, tok) => acc + (aStem.includes(tok) ? 1 : 0), 0);
      const bScore = tokens.reduce((acc, tok) => acc + (bStem.includes(tok) ? 1 : 0), 0);
      if (aScore !== bScore) return bScore - aScore;
    }
    return (b.lastModified - a.lastModified) || a.name.localeCompare(b.name);
  });
}
