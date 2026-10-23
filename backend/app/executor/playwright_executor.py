import asyncio
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Download
from app.models.actions import ActionStep
from app.models.guardrail import ValidationResult
from app.guardrails.safety_gate import SafetyGate
from app.verifier.outcome_verifier import OutcomeVerifier
from app.recovery.engine import RecoveryEngine
from app.inspector.dom_inspector import DOMInspector
from app.config import settings

class PlaywrightExecutor:
    """
    Persistent, production-grade Playwright browser execution loop with
    pre-execution guardrail validation, real-time screenshot screencasting,
    typed browser actions, artifact management, and outcome verification.
    """

    def __init__(
        self,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        frame_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        headless: Optional[bool] = None
    ):
        self.event_callback = event_callback
        self.frame_callback = frame_callback
        self.headless = settings.BROWSER_HEADLESS if headless is None else headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_running = False
        self.is_paused = False
        self.is_cancelled = False
        self._is_navigating = False
        self._stream_task: Optional[asyncio.Task] = None

    async def initialize(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-background-media-suspend",
                "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
                "--enable-zero-copy",
                "--ignore-gpu-blocklist"
            ]
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    slow_mo=settings.BROWSER_SLOWMO_MS,
                    args=launch_args
                )
            except Exception as launch_err:
                # Resilient fallback: locate existing chrome-win64/chrome.exe in ms-playwright
                ms_pw = Path(os.path.expanduser("~")) / "AppData" / "Local" / "ms-playwright"
                candidates = list(ms_pw.glob("chromium-*/chrome-win64/chrome.exe"))
                if candidates and candidates[0].exists():
                    self.browser = await self.playwright.chromium.launch(
                        executable_path=str(candidates[0]),
                        headless=self.headless,
                        slow_mo=settings.BROWSER_SLOWMO_MS,
                        args=launch_args
                    )
                else:
                    raise launch_err
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            self.is_running = True
            self.start_streaming()

    def start_streaming(self):
        if not self._stream_task or self._stream_task.done():
            self._stream_task = asyncio.create_task(self._stream_loop())

    def stop_streaming(self):
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()

    async def _stream_loop(self):
        """Continuously streams screencast frames smoothly without starving the Playwright event loop."""
        while self.is_running:
            if self.page and not self.is_paused and not self._is_navigating:
                try:
                    await self.capture_frame()
                except Exception:
                    pass
            try:
                is_video = bool(self.page and self.page.url and any(self.page.url.lower().endswith(ext) for ext in [".mkv", ".mp4", ".webm", ".avi", ".mov"]))
                await asyncio.sleep(1.2 if is_video else 0.8)
            except asyncio.CancelledError:
                break

    async def capture_frame(self) -> Optional[str]:
        """Captures a JPEG screenshot encoded in Base64 for live UI screencast."""
        if not self.page or self._is_navigating:
            return None
        try:
            is_video_page = bool(self.page.url and any(self.page.url.lower().endswith(ext) for ext in [".mkv", ".mp4", ".webm", ".avi", ".mov"]))
            quality = 40 if is_video_page else 60
            screenshot_bytes = await self.page.screenshot(type="jpeg", quality=quality)
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            if self.frame_callback:
                await self.frame_callback(b64)
            return b64
        except Exception:
            return None

    async def execute_step(
        self,
        step: ActionStep,
        mission_id: str,
        allowed_domains: List[str],
        demo_mode: bool = False,
        approval_granted: bool = False,
        require_approval_for_high_risk: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a single typed action step with pre-execution safety gating,
        real-time inspection, action execution, and post-execution verification.
        """
        if not self.page:
            await self.initialize()

        # 1. Pre-execution Safety Gate Validation
        validation: ValidationResult = await SafetyGate.validate_action(
            step=step,
            page=self.page,
            allowed_domains=allowed_domains,
            demo_mode=demo_mode,
            approval_granted=approval_granted,
            require_approval_for_high_risk=require_approval_for_high_risk
        )

        if not validation.can_proceed:
            return {
                "success": False,
                "status": "rejected" if not validation.requires_approval else "awaiting_approval",
                "validation": validation.model_dump(),
                "error": validation.rejection_reason or "Safety gate rejected action.",
                "requires_approval": validation.requires_approval,
                "requires_replanning": validation.requires_replanning
            }

        # 2. Execute Typed Action
        step_result: Dict[str, Any] = {"success": False}
        artifact_path: Optional[Path] = None

        try:
            if step.action_type == "navigate":
                dest_url = step.input_value or ""
                timeout = max(step.timeout_ms or 15000, 30000)
                self._is_navigating = True
                try:
                    await self.page.goto(dest_url, timeout=timeout, wait_until="domcontentloaded")
                except Exception:
                    try:
                        await self.page.goto(dest_url, timeout=12000, wait_until="commit")
                    except Exception:
                        pass
                finally:
                    self._is_navigating = False

                await self.page.wait_for_timeout(600)
                # Auto dismiss common cookie / consent banners if present
                try:
                    consent_btn = self.page.locator('button[aria-label*="Accept"], button:has-text("Accept all"), button:has-text("I agree"), ytd-consent-bump-v2-lightbox button, #introAgreeButton').first
                    if await consent_btn.is_visible():
                        await consent_btn.click()
                        await self.page.wait_for_timeout(300)
                except Exception:
                    pass

                step_result = {"success": True, "final_url": self.page.url}

            elif step.action_type == "request_approval":
                step_result = {"success": True, "approved": True}

            elif step.action_type == "click":
                target = step.target_locator_value or ""
                locator = self.page.locator(target).first
                # For direct HTML5 video element interaction (play/pause toggle prevention):
                # only trigger evaluation if target specifically targets <video> tag
                is_html5_video = target.strip() in ["video", "video.html5-main-video", "video.video-stream"] or target.strip().startswith("video[")
                if is_html5_video:
                    try:
                        await self.page.evaluate("""() => {
                            const v = document.querySelector('video');
                            if (v) {
                                v.muted = false;
                                if (v.paused) {
                                    v.play().catch(() => {});
                                }
                            }
                        }""")
                    except Exception:
                        pass
                else:
                    try:
                        href = None
                        try:
                            href = await locator.get_attribute("href", timeout=3000)
                        except Exception:
                            pass
                        
                        if not href:
                            try:
                                a_sub = locator.locator("a[href*='/watch?v=']").first
                                href = await a_sub.get_attribute("href", timeout=2000)
                            except Exception:
                                pass

                        if href and (href.startswith("/watch?v=") or "youtube.com/watch" in href):
                            watch_url = href if href.startswith("http") else f"https://www.youtube.com{href}"
                            self._is_navigating = True
                            try:
                                await self.page.goto(watch_url, timeout=max(step.timeout_ms or 15000, 30000), wait_until="domcontentloaded")
                            finally:
                                self._is_navigating = False
                        elif href and href.startswith("http"):
                            self._is_navigating = True
                            try:
                                await self.page.goto(href, timeout=max(step.timeout_ms or 15000, 30000), wait_until="domcontentloaded")
                            finally:
                                self._is_navigating = False
                        else:
                            await locator.click(timeout=step.timeout_ms or 6000)
                    except Exception:
                        try:
                            await locator.click(timeout=step.timeout_ms or 6000)
                        except Exception:
                            try:
                                await locator.dispatch_event("click")
                            except Exception:
                                pass

                await self.page.wait_for_timeout(300)
                if ("video" in target or "play" in step.intent.lower() or "youtube" in (self.page.url or "")) and not (self.page.url or "").startswith("file:"):
                    try:
                        await self.page.evaluate("""() => {
                            const handleMedia = () => {
                                if (window.location.hostname.includes('youtube.com')) {
                                    const skipBtns = [
                                        '.ytp-skip-ad-button',
                                        '.ytp-ad-skip-button-modern',
                                        '.ytp-ad-skip-button',
                                        'button.ytp-ad-skip-button-text',
                                        '.ytp-ad-overlay-close-button',
                                        'button[aria-label*="Skip"]'
                                    ];
                                    for (const sel of skipBtns) {
                                        const b = document.querySelector(sel);
                                        if (b && b.offsetParent !== null) { b.click(); }
                                    }
                                    const adContainer = document.querySelector('.ad-showing, .ad-interrupting');
                                    if (adContainer) {
                                        const ad = adContainer.querySelector('video');
                                        if (ad && isFinite(ad.duration) && ad.duration > 0 && ad.currentTime < ad.duration - 0.2) {
                                            ad.currentTime = ad.duration - 0.1;
                                        }
                                    }
                                }
                                const v = document.querySelector('video');
                                if (v) {
                                    if (v.paused) {
                                        v.muted = false;
                                        v.play().catch(() => {});
                                    }
                                    if (v.requestFullscreen) {
                                        v.requestFullscreen().catch(() => {});
                                    }
                                }
                            };
                            if (!window.__vector_media_keeper) {
                                window.__vector_media_keeper = setInterval(handleMedia, 1200);
                            }
                            handleMedia();
                        }""")
                    except Exception:
                        pass
                step_result = {"success": True, "clicked_selector": target}

            elif step.action_type == "fill":
                target = step.target_locator_value or ""
                val = step.input_value or ""
                locator = self.page.locator(target).first
                await locator.fill(val, timeout=step.timeout_ms)
                step_result = {"success": True, "filled_selector": target}

            elif step.action_type == "select_option":
                target = step.target_locator_value or ""
                val = step.input_value or ""
                locator = self.page.locator(target).first
                await locator.select_option(val, timeout=step.timeout_ms)
                step_result = {"success": True, "selected_option": val}

            elif step.action_type == "read_text":
                target = step.target_locator_value or "body"
                locator = self.page.locator(target).first
                text = await locator.inner_text(timeout=step.timeout_ms)
                step_result = {"success": True, "text": text}

            elif step.action_type == "wait_for_condition":
                target = step.target_locator_value
                timeout = max(step.timeout_ms or 10000, 15000)
                if target:
                    try:
                        await self.page.wait_for_selector(target, timeout=timeout, state="attached")
                    except Exception:
                        await self.page.wait_for_timeout(2000)
                else:
                    await self.page.wait_for_timeout(min(timeout, 3000))
                step_result = {"success": True, "condition_met": True}

            elif step.action_type == "extract_records":
                target = step.target_locator_value or "tbody tr"
                rows = await self.page.locator(target).all()
                extracted = []
                for idx, row in enumerate(rows):
                    cells = await row.locator("td").all()
                    if cells:
                        cell_texts = [await c.inner_text() for c in cells]
                        extracted.append({"row_index": idx + 1, "values": cell_texts})
                step_result = {"success": True, "records": extracted, "count": len(extracted)}

            elif step.action_type == "download_file":
                target = step.target_locator_value or ""
                locator = self.page.locator(target).first
                
                # Expect download event
                async with self.page.expect_download(timeout=step.timeout_ms) as download_info:
                    await locator.click()
                download: Download = await download_info.value

                suggested_filename = download.suggested_filename or f"download_{step.step_id}.dat"
                # Keep safe filename
                safe_name = os.path.basename(suggested_filename).replace("..", "").replace("/", "")
                artifact_dir = settings.absolute_artifacts_dir / mission_id
                artifact_dir.mkdir(parents=True, exist_ok=True)
                artifact_path = artifact_dir / safe_name
                await download.save_as(str(artifact_path))

                step_result = {
                    "success": True,
                    "artifact_path": str(artifact_path),
                    "filename": safe_name,
                    "file_size_bytes": artifact_path.stat().st_size
                }

            elif step.action_type == "launch_app":
                from app.utils.system_operator import AppLauncher
                target_query = step.input_value or step.intent
                res = AppLauncher.launch(target_query)
                if res.get("mode") == "web_fallback" and res.get("web_url"):
                    web_url = res["web_url"]
                    self._is_navigating = True
                    try:
                        await self.page.goto(web_url, timeout=20000, wait_until="domcontentloaded")
                    finally:
                        self._is_navigating = False
                    res["final_url"] = self.page.url
                step_result = res

            elif step.action_type == "system_command":
                from app.utils.system_operator import SystemOptimizer
                res = SystemOptimizer.optimize_pc()
                step_result = res

            # Capture live screencast frame after interaction
            await self.capture_frame()

        except Exception as e:
            error_text = str(e)
            fail_class = RecoveryEngine.classify_failure(step, error_text)
            return {
                "success": False,
                "status": "failed",
                "validation": validation.model_dump(),
                "failure_classification": fail_class,
                "error": error_text
            }

        # 3. Post-execution Outcome Verification
        verification = await OutcomeVerifier.verify_step_outcome(
            step=step,
            page=self.page,
            execution_result=step_result,
            artifact_path=artifact_path
        )

        return {
            "success": verification.get("verified", False),
            "status": "completed" if verification.get("verified", False) else "failed",
            "validation": validation.model_dump(),
            "verification": verification,
            "result_data": step_result,
            "artifact_path": str(artifact_path) if artifact_path else None
        }

    async def close(self):
        self.stop_streaming()
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.is_running = False
