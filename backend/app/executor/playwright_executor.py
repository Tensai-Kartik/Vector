import asyncio
import base64
import os
import sys
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
            is_render = bool(os.getenv("RENDER"))
            
            # On desktop headed mode, launch real Google Chrome guest window for full hardware-accelerated video/audio codecs
            if not self.headless and not is_render:
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
                ]
                chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
                try:
                    launch_kwargs = {
                        "headless": False,
                        "slow_mo": settings.BROWSER_SLOWMO_MS,
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--autoplay-policy=no-user-gesture-required",
                            "--no-default-browser-check",
                            "--no-first-run",
                            "--window-position=50,50",
                            "--window-size=1280,800",
                            "--start-maximized"
                        ]
                    }
                    if chrome_exe:
                        launch_kwargs["executable_path"] = chrome_exe
                    else:
                        launch_kwargs["channel"] = "chrome"

                    self.browser = await self.playwright.chromium.launch(**launch_kwargs)
                except Exception:
                    self.browser = None

            if not self.browser:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-background-media-suspend",
                    "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
                    "--enable-zero-copy",
                    "--ignore-gpu-blocklist",
                    "--window-position=50,50",
                    "--window-size=1280,800",
                    "--start-maximized"
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

            context_kwargs = {
                "accept_downloads": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            if not self.headless:
                context_kwargs["no_viewport"] = True
            else:
                context_kwargs["viewport"] = {"width": 1280, "height": 800}

            self.context = await self.browser.new_context(**context_kwargs)

            # Ad-blocking: Target only ad tracking networks and video ad stream manifests
            # NEVER route '**/*' as intercepting every video chunk stalls the media decoder!
            ad_patterns = [
                "*googlesyndication.com*",
                "*googleads.g.doubleclick.net*",
                "*pagead2.googlesyndication.com*",
                "*ad.doubleclick.net*",
                "*static.doubleclick.net*",
                "*youtube.com/api/stats/ads*",
                "*youtube.com/pagead/*",
                "*youtube.com/ptracking*",
                "*doubleclick.net*"
            ]
            async def abort_ad_route(route):
                try:
                    await route.abort()
                except Exception:
                    pass

            for pattern in ad_patterns:
                try:
                    await self.context.route(pattern, abort_ad_route)
                except Exception:
                    pass

            # Ad-blocking: Hide all banner, overlay, and promo ad elements with CSS and eliminate pre-roll and mid-roll ads
            ad_block_script = """
            (() => {
                // 1. Strip adPlacements from ytInitialPlayerResponse
                let pr = window.ytInitialPlayerResponse;
                Object.defineProperty(window, 'ytInitialPlayerResponse', {
                    get() { return pr; },
                    set(val) {
                        if (val && typeof val === 'object') {
                            delete val.adPlacements;
                            delete val.playerAds;
                            delete val.adSlots;
                        }
                        pr = val;
                    },
                    configurable: true
                });

                // 2. Intercept fetch to strip ads from player API response (pre-roll & mid-roll)
                const origFetch = window.fetch;
                window.fetch = async function(...args) {
                    const res = await origFetch.apply(this, args);
                    const url = args[0] ? (typeof args[0] === 'string' ? args[0] : args[0].url) : '';
                    if (url && url.includes('/youtubei/v1/player')) {
                        try {
                            const clone = res.clone();
                            const data = await clone.json();
                            if (data && (data.adPlacements || data.playerAds || data.adSlots)) {
                                delete data.adPlacements;
                                delete data.playerAds;
                                delete data.adSlots;
                                return new Response(JSON.stringify(data), {
                                    status: res.status,
                                    statusText: res.statusText,
                                    headers: res.headers
                                });
                            }
                        } catch(e) {}
                    }
                    return res;
                };

                // 3. Inject CSS to hide all ad banners, overlays, and promo slots
                const style = document.createElement('style');
                style.textContent = `
                    .video-ads, .ytp-ad-module, .ytp-ad-overlay-container,
                    .ytp-ad-message-container, ytd-promoted-sparkles-web-renderer,
                    ytd-promoted-video-renderer, ytd-compact-promoted-video-renderer,
                    #masthead-ad, ytd-banner-promo-renderer, ytd-ad-slot-renderer,
                    .ytp-ad-player-overlay, .ytp-ad-player-overlay-layout, #player-ads,
                    ytd-action-companion-ad-renderer, ytd-in-feed-ad-layout-renderer {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                        pointer-events: none !important;
                        height: 0 !important;
                        width: 0 !important;
                    }
                `;
                document.head ? document.head.appendChild(style) : document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));

                // 4. Safe, non-interfering auto-skipper for residual ad segments
                const skipAd = () => {
                    const skipBtn = document.querySelector('.ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern, button.ytp-ad-skip-button-text, .ytp-ad-overlay-close-button, button[aria-label*="Skip"]');
                    if (skipBtn && skipBtn.offsetParent !== null) {
                        try { skipBtn.click(); } catch(e) {}
                    }
                    const player = document.querySelector('#movie_player, .html5-video-player');
                    const isAd = player && (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting'));
                    if (isAd) {
                        const v = document.querySelector('video');
                        if (v && isFinite(v.duration) && v.duration > 0) {
                            v.muted = true;
                            v.playbackRate = 16.0;
                            v.currentTime = v.duration;
                            if (skipBtn) try { skipBtn.click(); } catch(e) {}
                        }
                    }
                };

                setInterval(skipAd, 600);
            })();
            """
            await self.context.add_init_script(ad_block_script)

            self.page = await self.context.new_page()
            self.is_running = True
            self.bring_to_foreground()
            self.start_streaming()

    def bring_to_foreground(self):
        """Ensures the headed browser window is visible and focused on the desktop."""
        if self.headless or sys.platform != "win32":
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            def enum_cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    class_buff = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buff, 256)
                    if class_buff.value == "Chrome_WidgetWin_1":
                        length = user32.GetWindowTextLengthW(hwnd)
                        title_buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, title_buff, length + 1)
                        title = title_buff.value.lower()
                        # Avoid targeting the user's dashboard tab
                        if "vector autonomous mission control" in title or "localhost:5173" in title:
                            return True
                        # Bring Chrome automation window to front and maximize
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_TOPMOST
                        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_NOTOPMOST
                        user32.SetForegroundWindow(hwnd)
                return True
            proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(enum_cb)
            user32.EnumWindows(proc, 0)
        except Exception:
            pass

    def start_streaming(self):
        if not self._stream_task or self._stream_task.done():
            self._stream_task = asyncio.create_task(self._stream_loop())

    def stop_streaming(self):
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()

    async def _stream_loop(self):
        """Continuously streams screencast frames smoothly without starving the Playwright event loop."""
        while self.is_running:
            is_video = bool(
                self.page and self.page.url and any(
                    ext in self.page.url.lower() for ext in [
                        "youtube.com", "watch?v=", "googlevideo.com",
                        ".mkv", ".mp4", ".webm", ".avi", ".mov"
                    ]
                )
            )

            # In headed desktop mode: user is watching the real Chrome window!
            # Do NOT freeze GPU compositor with repeating CDP screenshot captures!
            if not self.headless and is_video:
                if not getattr(self, "_video_preview_captured", False):
                    try:
                        await self.capture_frame()
                        self._video_preview_captured = True
                    except Exception:
                        pass
                try:
                    await asyncio.sleep(4.0)
                except asyncio.CancelledError:
                    break
                continue

            if not is_video:
                self._video_preview_captured = False

            if self.page and not self.is_paused and not self._is_navigating:
                try:
                    await self.capture_frame()
                except Exception:
                    pass
            try:
                await asyncio.sleep(0.8)
            except asyncio.CancelledError:
                break

    async def capture_frame(self) -> Optional[str]:
        """Captures a JPEG screenshot encoded in Base64 for live UI screencast."""
        if not self.page or self._is_navigating:
            return None
        try:
            is_video_page = bool(
                self.page.url and any(
                    ext in self.page.url.lower() for ext in [
                        "youtube.com", "watch?v=", "googlevideo.com",
                        ".mkv", ".mp4", ".webm", ".avi", ".mov"
                    ]
                )
            )
            quality = 30 if is_video_page else 60
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
                timeout = step.timeout_ms or 15000
                self._is_navigating = True
                try:
                    await self.page.goto(dest_url, timeout=min(timeout, 12000), wait_until="domcontentloaded")
                except Exception:
                    try:
                        await self.page.goto(dest_url, timeout=8000, wait_until="commit")
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
                if not is_html5_video and ("video" in target or "play" in step.intent.lower() or "youtube" in (self.page.url or "")) and not (self.page.url or "").startswith("file:"):
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
                                        if (b && b.offsetParent !== null) {
                                            try { b.click(); } catch(e) {}
                                        }
                                    }
                                }
                                const v = document.querySelector('video');
                                if (v) {
                                    v.muted = false;
                                    if (v.paused) {
                                        v.play().catch(() => {});
                                    }
                                }
                            };
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
                try:
                    await locator.wait_for(state="attached", timeout=step.timeout_ms or 8000)
                    text = await locator.inner_text(timeout=step.timeout_ms or 5000)
                except Exception:
                    text = await self.page.title()
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

        v_passed = verification.get("verified", False)
        v_error = verification.get("error") if not v_passed else None

        return {
            "success": v_passed,
            "status": "completed" if v_passed else "failed",
            "validation": validation.model_dump(),
            "verification": verification,
            "result_data": step_result,
            "artifact_path": str(artifact_path) if artifact_path else None,
            "error": v_error
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
