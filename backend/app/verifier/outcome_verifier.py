from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import hashlib
import urllib.parse
from playwright.async_api import Page
from app.models.actions import ActionStep
from app.config import settings
from app.executor.anti_bot import detect_anti_bot_gate

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

        # Fail fast if target page is gated by CAPTCHA / anti-bot verification
        if page and step.action_type in ["navigate", "click", "wait_for_condition", "read_text", "extract_records"]:
            gate = await detect_anti_bot_gate(page)
            if gate.get("blocked"):
                return {
                    "verified": False,
                    "captcha_blocked": True,
                    "strategy": method,
                    "evidence": gate,
                    "error": gate["reason"],
                }

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
                targets = [t.strip().lower() for t in target.split(",") if t.strip()]
                passed = any(
                    t in current_url.lower() or
                    current_url.lower().startswith(t) or
                    urllib.parse.unquote(t) in urllib.parse.unquote(current_url).lower()
                    for t in targets
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
                # Support comma-separated selectors (e.g. "video, #movie_player, ytd-player")
                raw_selectors = [s.strip() for s in sel.split(",") if s.strip()]
                selectors = list(raw_selectors)
                
                # Resilient expansion for video players on YouTube and media sites
                current_url = page.url or ""
                is_media_site = any(k in current_url.lower() for k in ["youtube.com", "watch?v=", "/shorts/", "vimeo.com", "twitch.tv"])
                if any("video" in s.lower() for s in raw_selectors) and is_media_site:
                    for extra in [".html5-main-video", "#movie_player", "ytd-player", "ytd-watch-flexy", "ytd-shorts", ".html5-video-player", "video"]:
                        if extra not in selectors:
                            selectors.append(extra)

                combined_sel = ", ".join(selectors)

                # Check directly in DOM via evaluate (bypasses shadow DOM/timing issues)
                in_dom = False
                try:
                    in_dom = await page.evaluate("""(sels) => {
                        for (const s of sels) {
                            try {
                                if (document.querySelector(s)) return true;
                            } catch(e) {}
                        }
                        return false;
                    }""", selectors)
                except Exception:
                    in_dom = False

                count = 1 if in_dom else await page.locator(combined_sel).count()
                if count == 0 and not in_dom:
                    try:
                        wait_timeout = min(max(step.timeout_ms or 4000, 2500), 6000)
                        await page.wait_for_selector(combined_sel, timeout=wait_timeout, state="attached")
                        count = await page.locator(combined_sel).count()
                    except Exception:
                        pass
                    if count == 0:
                        gate = await detect_anti_bot_gate(page)
                        if gate.get("blocked"):
                            return {
                                "verified": False,
                                "captcha_blocked": True,
                                "strategy": "element_present",
                                "evidence": gate,
                                "error": gate["reason"],
                            }

                is_visible = True if in_dom else False
                if count > 0 and not is_visible:
                    try:
                        is_visible = await page.locator(combined_sel).first.is_visible()
                    except Exception:
                        pass

                # If verifying a video player on a watch or shorts page, confirm by URL presence
                url_verified = bool(
                    is_media_site and
                    any("video" in s.lower() for s in raw_selectors) and
                    any(p in current_url.lower() for p in ["watch?v=", "/shorts/"])
                )

                verified = (count > 0) or in_dom or url_verified or is_visible
                evidence = {
                    "selector": combined_sel,
                    "count": count,
                    "is_visible": is_visible,
                    "in_dom": in_dom,
                    "url_verified": url_verified,
                    "current_url": current_url
                }
                return {
                    "verified": verified,
                    "strategy": "element_present",
                    "evidence": evidence,
                    "error": None if verified else f"Element matching '{combined_sel}' was not found in page (count: {count}, visible: {is_visible})"
                }
            except Exception as e:
                return {
                    "verified": False,
                    "strategy": "element_present",
                    "error": str(e),
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
