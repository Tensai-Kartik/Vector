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
from app.executor.anti_bot import detect_anti_bot_gate

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
        self._is_executing_step = False
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
                            "--new-window",
                            "--window-position=0,0",
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
                    "--window-size=1280,800"
                ]
                # Headless Linux cloud containers need GPU disabled and audio muted
                if self.headless or sys.platform != "win32":
                    launch_args.extend([
                        "--disable-gpu",
                        "--hide-scrollbars",
                        "--mute-audio"
                    ])
                else:
                    launch_args.extend([
                        "--enable-zero-copy",
                        "--ignore-gpu-blocklist",
                        "--window-position=50,50",
                        "--start-maximized"
                    ])
                effective_slow_mo = 0 if self.headless else settings.BROWSER_SLOWMO_MS
                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=self.headless,
                        slow_mo=effective_slow_mo,
                        args=launch_args
                    )
                except Exception as launch_err:
                    err_msg = str(launch_err)
                    # 1. On Windows desktop, try locating local AppData ms-playwright
                    ms_pw = Path(os.path.expanduser("~")) / "AppData" / "Local" / "ms-playwright"
                    candidates = list(ms_pw.glob("chromium-*/chrome-win64/chrome.exe"))
                    if candidates and candidates[0].exists():
                        try:
                            self.browser = await self.playwright.chromium.launch(
                                executable_path=str(candidates[0]),
                                headless=self.headless,
                                slow_mo=effective_slow_mo,
                                args=launch_args
                            )
                        except Exception:
                            self.browser = None

                    # 2. Resilient cloud auto-heal: if Chromium binary is missing, install on the fly
                    if not self.browser and ("doesn't exist" in err_msg.lower() or "playwright install" in err_msg.lower()):
                        print(f"[Playwright] Chromium binary not found ({err_msg}). Initiating non-blocking auto-install in environment...")
                        try:
                            # Use DEVNULL for stdout to prevent OS pipe buffer deadlocks from high-frequency download progress output
                            install_env = dict(os.environ)
                            if "PLAYWRIGHT_BROWSERS_PATH" not in install_env:
                                install_env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
                            proc = await asyncio.create_subprocess_exec(
                                sys.executable, "-m", "playwright", "install", "chromium",
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.PIPE,
                                env=install_env
                            )
                            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=85)
                            err_output = (stderr.decode() if stderr else "").strip()
                            print(f"[Playwright] Chromium download finished (exit code {proc.returncode}). Retrying browser launch...")
                            if proc.returncode != 0 and err_output:
                                print(f"[Playwright] Install warning/error: {err_output}")
                            self.browser = await self.playwright.chromium.launch(
                                headless=self.headless,
                                slow_mo=effective_slow_mo,
                                args=launch_args
                            )
                        except Exception as install_err:
                            print(f"[Playwright] Auto-install failed: {install_err}")
                            raise RuntimeError(f"Browser launch failed: Chromium is not installed. Add 'playwright install chromium' to your Render Build Command. (Details: {install_err})")
                    elif not self.browser:
                        raise launch_err

            browser_ver = getattr(self.browser, "version", "130.0.0.0") or "130.0.0.0"
            platform_token = "Windows NT 10.0; Win64; x64" if sys.platform == "win32" else "X11; Linux x86_64"
            context_kwargs = {
                "accept_downloads": True,
                "user_agent": f"Mozilla/5.0 ({platform_token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_ver} Safari/537.36"
            }
            if not self.headless:
                context_kwargs["no_viewport"] = True
            else:
                context_kwargs["viewport"] = {"width": 1280, "height": 800}

            self.context = await self.browser.new_context(**context_kwargs)

            # Automatically switch active target when a click/link opens a new browser tab
            def _handle_new_page(new_page: Page):
                self.page = new_page
                try:
                    asyncio.create_task(new_page.bring_to_front())
                except Exception:
                    pass

            self.context.on("page", _handle_new_page)

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

            # Simulate Alt key event to unlock Windows OS foreground lock
            VK_MENU = 0x12
            KEYEVENTF_KEYUP = 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

            def enum_cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    class_buff = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buff, 256)
                    if class_buff.value == "Chrome_WidgetWin_1":
                        length = user32.GetWindowTextLengthW(hwnd)
                        title_buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, title_buff, length + 1)
                        title = title_buff.value.lower()
                        # Strictly skip any window belonging to the Mission Control dashboard
                        if any(k in title for k in ["vector", "localhost", "5173", "autonomous web operator"]):
                            return True
                        # Force the Chrome automation window to the very top and maximize
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                        user32.BringWindowToTop(hwnd)
                        # HWND_TOPMOST (-1) with SWP_SHOWWINDOW (0x0040)
                        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
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
        """Continuously streams screencast frames at configured interval without starving active step execution."""
        interval_sec = max(0.35, (settings.SCREENSHOT_STREAM_INTERVAL_MS or 800) / 1000.0)
        while self.is_running:
            if (
                self.page
                and not self.is_paused
                and not self._is_navigating
                and not self._is_executing_step
            ):
                try:
                    await self.capture_frame()
                except Exception:
                    pass
            try:
                await asyncio.sleep(interval_sec)
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
            quality = 28 if is_video_page else 55
            screenshot_bytes = await self.page.screenshot(type="jpeg", quality=quality, timeout=1000)
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            if self.frame_callback:
                await self.frame_callback(b64)
            return b64
        except Exception:
            return None

    async def _dismiss_popups_and_consent(self):
        """Auto dismiss consent modals, cookie notices, and overlays across web services."""
        if not self.page:
            return
        try:
            await self.page.evaluate("""() => {
                const dismissSelectors = [
                    'ytd-consent-bump-v2-lightbox button',
                    '#consent-bump button',
                    'button[aria-label*="Accept all"]',
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="I agree"]',
                    '#introAgreeButton',
                    'ytd-button-renderer#dismiss-button',
                    'tp-yt-paper-dialog #dismiss-button',
                    'button.yt-spec-button-shape-next--filled[aria-label*="Accept"]',
                    'div.consent-bump-v2 button'
                ];
                for (const sel of dismissSelectors) {
                    try {
                        const btn = document.querySelector(sel);
                        if (btn && btn.offsetParent !== null) {
                            btn.click();
                        }
                    } catch(e) {}
                }
            }""")
        except Exception:
            pass

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
        self._is_executing_step = True

        try:
            if step.action_type == "navigate":
                dest_url = step.input_value or ""
                timeout = step.timeout_ms or 12000
                self._is_navigating = True
                try:
                    await self.page.goto(dest_url, timeout=min(timeout, 10000), wait_until="domcontentloaded")
                except Exception:
                    try:
                        await self.page.goto(dest_url, timeout=6000, wait_until="commit")
                    except Exception:
                        pass
                finally:
                    self._is_navigating = False

                await self.page.wait_for_timeout(150)
                try:
                    if not self.headless:
                        await self.page.bring_to_front()
                        self.bring_to_foreground()
                except Exception:
                    pass

                # Fast non-blocking consent cleanup
                await self._dismiss_popups_and_consent()

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
                        # Special resilient YouTube search result extraction:
                        if "youtube" in (self.page.url or "") and ("results" in (self.page.url or "") or "video" in target or "play" in step.intent.lower()):
                            try:
                                href = await self.page.evaluate("""() => {
                                    document.querySelectorAll('a[data-vector-yt-pick]').forEach(el => el.removeAttribute('data-vector-yt-pick'));
                                    // 1. First priority: regular full-length video renderer
                                    let picked = document.querySelector('ytd-video-renderer a#video-title[href*="/watch"], ytd-video-renderer a[href*="/watch"], a#video-title[href*="/watch"]');
                                    // 2. Second priority: any watch link on the page
                                    if (!picked) picked = document.querySelector('a[href*="/watch?v="]');
                                    // 3. Third priority: top short if no long video on screen
                                    if (!picked) picked = document.querySelector('ytd-reel-item-renderer a[href*="/shorts/"], ytm-shorts-lockup-view-model a[href*="/shorts/"], a[href*="/shorts/"]');
                                    if (picked) {
                                        picked.setAttribute('data-vector-yt-pick', '1');
                                        return picked.getAttribute('href') || picked.href;
                                    }
                                    return null;
                                }""")
                            except Exception:
                                href = None

                        if not href:
                            try:
                                href = await locator.get_attribute("href", timeout=1500)
                            except Exception:
                                pass
                        
                        if not href:
                            try:
                                a_sub = locator.locator("a[href*='/watch?v='], a[href*='/shorts/']").first
                                href = await a_sub.get_attribute("href", timeout=1500)
                            except Exception:
                                pass

                        if href and (href.startswith("/watch?v=") or href.startswith("/shorts/") or "youtube.com/watch" in href or "youtube.com/shorts" in href):
                            watch_url = href if href.startswith("http") else f"https://www.youtube.com{href}"
                            self._is_navigating = True
                            try:
                                clicked_via_spa = False
                                try:
                                    spa_loc = self.page.locator('a[data-vector-yt-pick="1"]').first
                                    if await spa_loc.count() > 0:
                                        await spa_loc.scroll_into_view_if_needed(timeout=1500)
                                        await spa_loc.click(timeout=3500)
                                        clicked_via_spa = True
                                except Exception:
                                    clicked_via_spa = False

                                if clicked_via_spa:
                                    try:
                                        await self.page.wait_for_url(
                                            lambda u: "watch?v=" in u or "/shorts/" in u or "/sorry/" in u,
                                            timeout=4500,
                                            wait_until="commit"
                                        )
                                    except Exception:
                                        pass

                                gate = await detect_anti_bot_gate(self.page)
                                cur_url = self.page.url or ""
                                if not gate.get("blocked") and "watch?v=" not in cur_url and "/shorts/" not in cur_url:
                                    await self.page.goto(
                                        watch_url,
                                        timeout=min(max(step.timeout_ms or 12000, 12000), 18000),
                                        wait_until="domcontentloaded"
                                    )
                                await self._dismiss_popups_and_consent()
                            finally:
                                self._is_navigating = False
                        elif href and href.startswith("http"):
                            self._is_navigating = True
                            try:
                                await self.page.goto(
                                    href,
                                    timeout=min(max(step.timeout_ms or 12000, 12000), 18000),
                                    wait_until="domcontentloaded"
                                )
                                await self._dismiss_popups_and_consent()
                            finally:
                                self._is_navigating = False
                        else:
                            try:
                                await locator.scroll_into_view_if_needed(timeout=1500)
                            except Exception:
                                pass
                            await locator.click(timeout=step.timeout_ms or 5000)
                    except Exception:
                        try:
                            await locator.click(timeout=step.timeout_ms or 6000)
                        except Exception:
                            try:
                                await locator.dispatch_event("click")
                            except Exception:
                                pass

                await self.page.wait_for_timeout(300)
                await self._dismiss_popups_and_consent()
                if not is_html5_video and ("video" in target or "play" in step.intent.lower() or "youtube" in (self.page.url or "")) and not (self.page.url or "").startswith("file:"):
                    try:
                        muted_js = "true" if self.headless else "false"
                        await self.page.evaluate(f"""() => {{
                            const handleMedia = () => {{
                                if (window.location.hostname.includes('youtube.com')) {{
                                    const skipBtns = [
                                        '.ytp-skip-ad-button',
                                        '.ytp-ad-skip-button-modern',
                                        '.ytp-ad-skip-button',
                                        'button.ytp-ad-skip-button-text',
                                        '.ytp-ad-overlay-close-button',
                                        'button[aria-label*="Skip"]'
                                    ];
                                    for (const sel of skipBtns) {{
                                        const b = document.querySelector(sel);
                                        if (b && b.offsetParent !== null) {{
                                            try {{ b.click(); }} catch(e) {{}}
                                        }}
                                    }}
                                }}
                                const v = document.querySelector('video');
                                if (v) {{
                                    v.muted = {muted_js};
                                    if (v.paused) {{
                                        v.play().catch(() => {{}});
                                    }}
                                }}
                            }};
                            handleMedia();
                        }}""")
                    except Exception:
                        pass
                if not self.headless:
                    try:
                        await self.page.bring_to_front()
                        self.bring_to_foreground()
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
                timeout = min(max(step.timeout_ms or 6000, 2000), 12000)
                gate = await detect_anti_bot_gate(self.page)
                if gate.get("blocked"):
                    step_result = {"success": False, "anti_bot_gate": gate}
                elif target:
                    check_target = target
                    if "video" in target and ("youtube" in (self.page.url or "") or "watch" in (self.page.url or "") or "shorts" in (self.page.url or "")):
                        check_target = "video, .html5-main-video, #movie_player, ytd-player, ytd-watch-flexy, ytd-shorts, .html5-video-player"
                    try:
                        await self.page.wait_for_selector(check_target, timeout=timeout, state="attached")
                    except Exception:
                        await self.page.wait_for_timeout(150)
                    
                    await self._dismiss_popups_and_consent()
                    # Trigger media playback
                    if "video" in target:
                        try:
                            muted_js = "true" if self.headless else "false"
                            await self.page.evaluate(f"""() => {{
                                const v = document.querySelector('video');
                                if (v) {{
                                    v.muted = {muted_js};
                                    if (v.paused) v.play().catch(() => {{}});
                                }}
                            }}""")
                        except Exception:
                            pass
                    step_result = {"success": True, "condition_met": True}
                else:
                    await self.page.wait_for_timeout(min(timeout, 1500))
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
            self._is_executing_step = False
            error_text = str(e)
            fail_class = RecoveryEngine.classify_failure(step, error_text)
            return {
                "success": False,
                "status": "failed",
                "validation": validation.model_dump(),
                "failure_classification": fail_class,
                "error": error_text
            }
        except BaseException:
            self._is_executing_step = False
            raise

        # 3. Post-execution Outcome Verification
        try:
            verification = await OutcomeVerifier.verify_step_outcome(
                step=step,
                page=self.page,
                execution_result=step_result,
                artifact_path=artifact_path
            )
        finally:
            self._is_executing_step = False

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
