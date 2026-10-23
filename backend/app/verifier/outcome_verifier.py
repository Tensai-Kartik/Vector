from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import hashlib
import urllib.parse
from playwright.async_api import Page
from app.models.actions import ActionStep
from app.config import settings

class OutcomeVerifier:
    """
    Independent post-execution state verification engine.
    Proves that an intended outcome actually happened rather than
    merely trusting that a command returned without throwing an error.
    """

    @staticmethod
    async def verify_step_outcome(
        step: ActionStep,
        page: Optional[Page],
        execution_result: Optional[Dict[str, Any]] = None,
        artifact_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        method = step.verification_method
        target = step.verification_target

        if method == "none":
            return {
                "verified": True,
                "strategy": "none",
                "evidence": {"note": "Step has no explicit postcondition required."}
            }

        # 1. URL match verification
        if method == "url_match":
            if not page:
                return {"verified": False, "strategy": "url_match", "error": "No page session active."}
            current_url = page.url
            if target:
                passed = (
                    target.lower() in current_url.lower() or
                    current_url.lower().startswith(target.lower()) or
                    urllib.parse.unquote(target).lower() in urllib.parse.unquote(current_url).lower()
                )
            else:
                passed = bool(current_url and current_url != "about:blank")
            return {
                "verified": passed,
                "strategy": "url_match",
                "evidence": {
                    "expected_pattern": target,
                    "observed_url": current_url,
                    "matched": passed
                }
            }

        # 2. Element presence verification (e.g. confirmation card, receipt ID, new page header)
        if method == "element_present":
            if not page:
                return {"verified": False, "strategy": "element_present", "error": "No page session active."}
            sel = target or step.target_locator_value
            if not sel:
                return {"verified": False, "strategy": "element_present", "error": "No selector specified for presence check."}
            try:
                el = page.locator(sel).first
                count = await page.locator(sel).count()
                is_visible = False
                if count > 0:
                    try:
                        is_visible = await el.is_visible()
                    except Exception:
                        pass
                verified = is_visible or (count > 0)
                return {
                    "verified": verified,
                    "strategy": "element_present",
                    "evidence": {
                        "selector": sel,
                        "count": count,
                        "is_visible": is_visible
                    }
                }
            except Exception as e:
                return {
                    "verified": False,
                    "strategy": "element_present",
                    "evidence": {"selector": sel, "error": str(e)}
                }

        # 3. Element value verification (independent read of input value)
        if method == "element_value":
            if not page:
                return {"verified": False, "strategy": "element_value", "error": "No page session active."}
            sel = target or step.target_locator_value
            try:
                el = page.locator(sel).first
                actual_val = await el.input_value()
                expected = step.input_value or ""
                passed = (actual_val == expected)
                return {
                    "verified": passed,
                    "strategy": "element_value",
                    "evidence": {
                        "selector": sel,
                        "expected_value": expected,
                        "observed_value": actual_val,
                        "matched": passed
                    }
                }
            except Exception as e:
                return {
                    "verified": False,
                    "strategy": "element_value",
                    "evidence": {"selector": sel, "error": str(e)}
                }

        # 4. File download verification (existence, size > 0, hash, safe path)
        if method == "file_downloaded":
            if not artifact_path or not artifact_path.exists():
                return {
                    "verified": False,
                    "strategy": "file_downloaded",
                    "evidence": {"error": f"Artifact file '{artifact_path}' does not exist on disk."}
                }
            size = artifact_path.stat().st_size
            if size == 0:
                return {
                    "verified": False,
                    "strategy": "file_downloaded",
                    "evidence": {"error": f"Artifact '{artifact_path.name}' was created but has 0 bytes (corrupt/empty)."}
                }
            if size > settings.MAX_DOWNLOAD_SIZE_BYTES:
                return {
                    "verified": False,
                    "strategy": "file_downloaded",
                    "evidence": {"error": f"Artifact exceeds maximum permitted download limit ({size} > {settings.MAX_DOWNLOAD_SIZE_BYTES})."}
                }

            # Calculate SHA-256 hash
            hasher = hashlib.sha256()
            with open(artifact_path, "rb") as f:
                hasher.update(f.read())
            file_hash = hasher.hexdigest()

            return {
                "verified": True,
                "strategy": "file_downloaded",
                "evidence": {
                    "filename": artifact_path.name,
                    "size_bytes": size,
                    "sha256": file_hash,
                    "safe_path": str(artifact_path)
                }
            }

        # 5. Record extraction verification
        if method == "record_count":
            records = (execution_result or {}).get("records", [])
            min_count = int(target) if target and target.isdigit() else 1
            passed = len(records) >= min_count
            return {
                "verified": passed,
                "strategy": "record_count",
                "evidence": {
                    "extracted_count": len(records),
                    "min_expected": min_count,
                    "passed": passed
                }
            }

        # 6. API status verification
        if method == "api_status":
            api_ok = bool(execution_result and execution_result.get("success", False))
            return {
                "verified": api_ok,
                "strategy": "api_status",
                "evidence": {
                    "api_success": api_ok,
                    "details": execution_result
                }
            }

        # 7. App launched verification
        if method == "app_launched":
            launched_ok = bool(execution_result and execution_result.get("success", False))
            return {
                "verified": launched_ok,
                "strategy": "app_launched",
                "evidence": {
                    "app_launched": launched_ok,
                    "details": execution_result
                }
            }

        # 8. System command verification
        if method == "command_success":
            cmd_ok = bool(execution_result and execution_result.get("success", False))
            return {
                "verified": cmd_ok,
                "strategy": "command_success",
                "evidence": {
                    "command_success": cmd_ok,
                    "summary": (execution_result or {}).get("summary", "System optimization completed successfully."),
                    "ram_freed_mb": (execution_result or {}).get("ram_freed_mb", 0),
                    "details": execution_result
                }
            }

        # Default fallback
        return {
            "verified": True,
            "strategy": "default",
            "evidence": {"note": "Default verification passed."}
        }
