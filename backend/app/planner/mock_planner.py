import urllib.parse
import re
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.planner.base import BasePlanner
from app.models.actions import ActionPlan, ActionStep
from app.models.inspector import PageObservation
from app.config import settings

class MockPlanner(BasePlanner):
    """
    Deterministic mock planner for automated testing, benchmarks,
    and offline operation without requiring LLM API keys.
    """

    async def create_plan(
        self,
        task: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None,
        demo_mode: bool = False
    ) -> ActionPlan:
        # Normalize common typos and variations
        norm_task = re.sub(r"\bopwn\b|\boepn\b|\bpoen\b", "open", task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bplsy\b|\bpaly\b|\bplayy\b", "play", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bdonwload\b|\bdownlaod\b|\bdownlod\b", "download", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bdownlaods\b|\bdonwloads\b", "downloads", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\byoutub\b|\bytube\b|\byt\b", "youtube", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bgoolge\b|\bgogle\b|\bgooglr\b", "google", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bwhatapp\b|\bwatsapp\b|\bwhatsap\b", "whatsapp", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bepci\b|\bepig\b", "epic", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bunncecsarry\b|\bunnecessary\b|\bunecessary\b", "unnecessary", norm_task, flags=re.IGNORECASE)
        norm_task = re.sub(r"\bproceses\b|\bprocessess\b", "processes", norm_task, flags=re.IGNORECASE)
        t_lower = norm_task.lower()
        base_url = f"http://127.0.0.1:{settings.PORT}" if demo_mode else "http://localhost:8000"

        # Scenario 1: Invoice Download
        if "invoice" in t_lower and ("download" in t_lower or "latest" in t_lower or "find" in t_lower):
            return ActionPlan(
                task=task,
                reasoning="Navigate to invoices portal, locate the newest invoice record INV-2026-004, inspect its detail view, and initiate verified file download.",
                allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent="Navigate to internal accounts payable invoices directory",
                        input_value=f"{base_url}/demo/invoices",
                        expected_postconditions="Invoice list page is loaded and displays table",
                        verification_method="url_match",
                        verification_target=f"{base_url}/demo/invoices"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="click",
                        intent="Click 'View Details' on the latest invoice INV-2026-004",
                        target_description="View button for invoice INV-2026-004",
                        target_locator_strategy="css",
                        target_locator_value="#view-INV-2026-004",
                        expected_postconditions="Invoice detail page for INV-2026-004 is active",
                        verification_method="element_present",
                        verification_target="#detail-invoice-id"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="download_file",
                        intent="Download invoice CSV file",
                        target_description="Download Invoice CSV button",
                        target_locator_strategy="css",
                        target_locator_value="#btn-download-detail",
                        expected_postconditions="CSV file downloaded into artifact directory with positive byte size",
                        verification_method="file_downloaded",
                        verification_target="INV-2026-004.csv"
                    )
                ]
            )

        # Scenario 2: Form submission with approval
        elif "form" in t_lower or "procurement" in t_lower or "requisition" in t_lower:
            return ActionPlan(
                task=task,
                reasoning="Navigate to procurement requisition form, fill vendor and amount fields, certify compliance, request approval, and submit.",
                allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent="Navigate to procurement requisition form",
                        input_value=f"{base_url}/demo/form",
                        expected_postconditions="Procurement form is visible",
                        verification_method="element_present",
                        verification_target="#procurement-form"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="fill",
                        intent="Enter approved vendor name",
                        target_locator_strategy="css",
                        target_locator_value="#vendor-name",
                        input_value="QuantumCore Systems",
                        expected_postconditions="Vendor name field populated",
                        verification_method="element_value",
                        verification_target="#vendor-name"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="fill",
                        intent="Enter requisition amount",
                        target_locator_strategy="css",
                        target_locator_value="#amount",
                        input_value="12500",
                        expected_postconditions="Amount field populated",
                        verification_method="element_value",
                        verification_target="#amount"
                    ),
                    ActionStep(
                        step_id="step_4",
                        action_type="select_option",
                        intent="Select budget category",
                        target_locator_strategy="css",
                        target_locator_value="#category",
                        input_value="cloud_compute",
                        expected_postconditions="Budget category selected",
                        verification_method="none"
                    ),
                    ActionStep(
                        step_id="step_5",
                        action_type="fill",
                        intent="Provide business justification",
                        target_locator_strategy="css",
                        target_locator_value="#justification",
                        input_value="Provisioning high-memory compute instances for batch verification runs.",
                        expected_postconditions="Justification filled",
                        verification_method="none"
                    ),
                    ActionStep(
                        step_id="step_6",
                        action_type="click",
                        intent="Check compliance certification checkbox",
                        target_locator_strategy="css",
                        target_locator_value="#approval-confirm",
                        expected_postconditions="Checkbox checked",
                        verification_method="none"
                    ),
                    ActionStep(
                        step_id="step_7",
                        action_type="click",
                        intent="Submit requisition for final processing",
                        target_locator_strategy="css",
                        target_locator_value="#submit-form-btn",
                        risk_classification="high",
                        expected_postconditions="Form submission confirmation banner and receipt ID displayed",
                        verification_method="element_present",
                        verification_target="#receipt-id"
                    )
                ]
            )

        # Scenario 3: Structured Records Extraction to CSV
        elif "extract" in t_lower or "records" in t_lower or "server" in t_lower:
            return ActionPlan(
                task=task,
                reasoning="Navigate to infrastructure fleet records, extract table data into structured JSON, and produce an export artifact.",
                allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent="Navigate to infrastructure fleet table",
                        input_value=f"{base_url}/demo/records",
                        verification_method="element_present",
                        verification_target="#records-table"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="extract_records",
                        intent="Extract structured records from fleet table",
                        target_description="Infrastructure nodes table rows",
                        target_locator_strategy="css",
                        target_locator_value="#records-table tbody tr",
                        expected_postconditions="Extracted rows parsed into JSON array with node IDs",
                        verification_method="record_count",
                        verification_target="10"
                    )
                ]
            )

        # Scenario 4: GitHub API / Fallback
        elif "github" in t_lower:
            return ActionPlan(
                task=task,
                reasoning="Query GitHub information using authorized direct API adapter (API-first).",
                allowed_domains=["api.github.com", "github.com"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="api_operation",
                        intent="Query GitHub repository metadata via REST API adapter",
                        input_value=task,
                        execution_method_preference="api",
                        verification_method="api_status"
                    )
                ]
            )

        # Scenario 5: Edge Case - Delayed Element Recovery
        elif "delayed" in t_lower or "recovery" in t_lower:
            return ActionPlan(
                task=task,
                reasoning="Navigate to edge cases page and wait for asynchronous delayed action button.",
                allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent="Navigate to Edge Case Sandbox",
                        input_value=f"{base_url}/demo/edge-cases",
                        verification_method="url_match",
                        verification_target=f"{base_url}/demo/edge-cases"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for delayed action button to render in DOM",
                        target_locator_value="#delayed-action-button",
                        timeout_ms=5000,
                        verification_method="element_present",
                        verification_target="#delayed-action-button"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="click",
                        intent="Click recovered delayed button",
                        target_locator_strategy="css",
                        target_locator_value="#delayed-action-button",
                        verification_method="none"
                    )
                ]
            )

        # Scenario 6: Non-existent element rejection (Guardrail test)
        elif "nonexistent" in t_lower or "missing" in t_lower or "reject" in t_lower:
            return ActionPlan(
                task=task,
                reasoning="Attempt interaction with a non-existent element to test pre-execution safety gate rejection.",
                allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent="Navigate to sandbox",
                        input_value=f"{base_url}/demo/invoices",
                        verification_method="url_match"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="click",
                        intent="Click phantom element that does not exist in DOM",
                        target_locator_strategy="css",
                        target_locator_value="#phantom-non-existent-button-xyz",
                        verification_method="none"
                    )
                ]
            )

        # Scenario 6B: Local Multi-Drive & Media Player (C:, D:, etc.)
        elif any(w in t_lower for w in ["downloads", "download", "media", "folder", "local file", "local video", "local audio", "my file", "my video", "videos", "my music", "drive", "movies", "trapped", "friends", "file://", "d:", "c:"]) and "youtube" not in t_lower and "invoice" not in t_lower and "github" not in t_lower:
            import os
            from pathlib import Path
            from app.utils.local_storage import LocalStorageManager

            target_dir, dir_label = LocalStorageManager.resolve_target_directory(task)
            wants_media = any(w in t_lower for w in ["media", "play", "video", "audio", "song", "webm", "mp4", "mkv", "movie"])

            if os.getenv("RENDER"):
                folder_hint = dir_label
                for kw, lbl in [
                    ("download", "Downloads"),
                    ("video", "Videos"),
                    ("movie", "Videos"),
                    ("music", "Music"),
                    ("song", "Music"),
                    ("audio", "Music"),
                    ("desktop", "Desktop"),
                    ("document", "Documents"),
                ]:
                    if kw in t_lower:
                        folder_hint = lbl
                        break
                return ActionPlan(
                    task=task,
                    reasoning=(
                        f"Cloud deployment cannot access your local PC '{folder_hint}' folder directly. "
                        "Requesting browser file/folder permission so you can select and play local media in the viewport."
                    ),
                    allowed_domains=["*"],
                    steps=[
                        ActionStep(
                            step_id="step_auth",
                            action_type="request_clarification",
                            intent=f"Select local media from your PC's {folder_hint} folder",
                            risk_classification="low",
                            metadata={
                                "action_required": "local_media_picker",
                                "requested_folder": folder_hint,
                                "wants_media_playback": wants_media,
                            },
                            expected_postconditions="Operator selects local media from PC folder",
                            verification_method="none",
                        )
                    ],
                )

            media_files = LocalStorageManager.find_media_files(target_dir)

            if media_files and wants_media:
                target_media = media_files[0]
                folder_url = target_dir.as_uri() if target_dir.exists() else "file:///"
                return ActionPlan(
                    task=task,
                    reasoning=f"Autonomous Local Storage task: Request permission for {dir_label}, launch '{target_media.name}' exclusively in native default desktop media player (VLC/Movies & TV) with hardware acceleration, and display {dir_label} directory view in browser viewport.",
                    allowed_domains=["*"],
                    steps=[
                        ActionStep(
                            step_id="step_auth",
                            action_type="request_approval",
                            intent=f"Authorize local storage access to {dir_label} ({len(media_files)} media files found)",
                            risk_classification="high",
                            expected_postconditions="Operator permission granted for local storage access",
                            verification_method="none"
                        ),
                        ActionStep(
                            step_id="step_1",
                            action_type="launch_app",
                            intent=f"Launch '{target_media.name}' in default desktop media player app",
                            input_value=str(target_media.resolve()),
                            expected_postconditions=f"Default desktop media player launched for {target_media.name}",
                            verification_method="app_launched"
                        ),
                        ActionStep(
                            step_id="step_2",
                            action_type="navigate",
                            intent=f"Display {dir_label} directory contents in browser view",
                            input_value=folder_url,
                            expected_postconditions=f"{dir_label} directory loaded",
                            verification_method="url_match",
                            verification_target="file:"
                        ),
                        ActionStep(
                            step_id="step_3",
                            action_type="read_text",
                            intent=f"Inspect folder content and verify active desktop playback of '{target_media.name}'",
                            target_locator_strategy="css",
                            target_locator_value="body",
                            verification_method="none"
                        )
                    ]
                )
            else:
                resolved_dir = target_dir if target_dir.exists() else (
                    Path(os.path.expanduser("~")) if Path(os.path.expanduser("~")).exists() else Path.cwd()
                )
                folder_url = resolved_dir.as_uri()
                return ActionPlan(
                    task=task,
                    reasoning=f"Navigate to {dir_label} with operator authorization.",
                    allowed_domains=["*"],
                    steps=[
                        ActionStep(
                            step_id="step_auth",
                            action_type="request_approval",
                            intent=f"Authorize local storage access to {dir_label}",
                            risk_classification="high",
                            expected_postconditions="Operator permission granted for local storage access",
                            verification_method="none"
                        ),
                        ActionStep(
                            step_id="step_1",
                            action_type="navigate",
                            intent=f"Open local directory: {dir_label}",
                            input_value=folder_url,
                            expected_postconditions=f"{dir_label} loaded",
                            verification_method="url_match",
                            verification_target="file:"
                        ),
                        ActionStep(
                            step_id="step_2",
                            action_type="read_text",
                            intent="Inspect folder content",
                            target_locator_strategy="css",
                            target_locator_value="body",
                            verification_method="none"
                        )
                    ]
                )

        # Scenario 7: YouTube Video Search & Playback
        elif "youtube" in t_lower or "carryminati" in t_lower or ("video" in t_lower and ("play" in t_lower or "watch" in t_lower)):
            from app.utils.youtube_resolver import extract_youtube_query

            query = extract_youtube_query(task)
            encoded_query = urllib.parse.quote_plus(query)
            return ActionPlan(
                task=task,
                reasoning=f"Autonomous YouTube task: Search for '{query}', locate top video result, open video player, and trigger playback.",
                allowed_domains=["youtube.com", "www.youtube.com", "googlevideo.com", "google.com"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent=f"Navigate to YouTube search for '{query}'",
                        input_value=f"https://www.youtube.com/results?search_query={encoded_query}",
                        timeout_ms=15000,
                        expected_postconditions="YouTube search results page loaded",
                        verification_method="url_match",
                        verification_target="youtube.com/results"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for video feed cards to render in DOM",
                        target_locator_value="ytd-video-renderer a#video-title, yt-lockup-view-model a, ytd-reel-item-renderer a, ytm-shorts-lockup-view-model a, a[href*='/watch'], a[href*='/shorts/']",
                        timeout_ms=12000,
                        verification_method="element_present",
                        verification_target="ytd-video-renderer, yt-lockup-view-model, ytd-reel-item-renderer, ytm-shorts-lockup-view-model, a[href*='/watch'], a[href*='/shorts/']"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="click",
                        intent=f"Click top video result for '{query}' and begin playback",
                        target_locator_strategy="css",
                        target_locator_value="ytd-video-renderer a#video-title, yt-lockup-view-model a[href*='/watch'], a#video-title, a[href*='/watch'], a[href*='/shorts/']",
                        timeout_ms=12000,
                        expected_postconditions="Video watch player is launched",
                        verification_method="url_match",
                        verification_target="watch?v=, /shorts/, youtube.com/watch, youtube.com/shorts"
                    ),
                    ActionStep(
                        step_id="step_4",
                        action_type="wait_for_condition",
                        intent="Confirm HTML5 video player is loaded and streaming",
                        target_locator_value="video, .html5-main-video, #movie_player, ytd-player, ytd-shorts",
                        timeout_ms=6000,
                        verification_method="element_present",
                        verification_target="video, .html5-main-video, #movie_player, ytd-player, ytd-shorts"
                    ),
                    ActionStep(
                        step_id="step_5",
                        action_type="read_text",
                        intent="Extract video title and confirm active playback session",
                        target_locator_strategy="css",
                        target_locator_value="#title h1, h1.ytd-watch-metadata, #info-contents h1, ytd-watch-metadata #title, ytd-reel-player-header-renderer h2, h2.title, title",
                        timeout_ms=5000,
                        expected_postconditions="Video title captured",
                        verification_method="none"
                    )
                ]
            )

        # Scenario 7B: Local Apps & Software Launcher (check locally installed first; fallback to web browser if absent)
        elif any(w in t_lower for w in [
            "whatsapp", "epic", "spotify", "discord", "steam", "calc", "calculator",
            "notepad", "vscode", "explorer", "taskmgr", "telegram", "zoom", "slack",
            "vlc", "notion", "figma", "canva"
        ]) or ("open" in t_lower and any(w in t_lower for w in ["app", "software", "launcher", "game", "games", "home"])):
            from app.utils.system_operator import AppLauncher
            avail = AppLauncher.check_app_availability(task)
            app_key = avail.get("app_key") or task
            app_name = avail.get("app_name") or task
            web_fallback = avail.get("web_fallback")
            installed_locally = bool(avail.get("installed_locally"))

            steps = [
                ActionStep(
                    step_id="step_1",
                    action_type="launch_app",
                    intent=f"Check & launch {app_name} (native app if installed locally, else browser web fallback)",
                    input_value=app_key,
                    expected_postconditions=f"{app_name} launched or web workspace active",
                    verification_method="app_launched"
                )
            ]
            if not installed_locally and web_fallback:
                steps.append(
                    ActionStep(
                        step_id="step_2",
                        action_type="navigate",
                        intent=f"Open {app_name} web version in browser (not installed locally)",
                        input_value=web_fallback,
                        expected_postconditions=f"{app_name} web workspace active",
                        verification_method="url_match",
                        verification_target=urllib.parse.urlparse(web_fallback).netloc
                    )
                )
            return ActionPlan(
                task=task,
                reasoning=(
                    f"Autonomous Application Operator: {app_name} is installed locally ({avail.get('mode')}); launching desktop app."
                    if installed_locally
                    else f"Autonomous Application Operator: {app_name} is not installed locally; falling back to browser web app ({web_fallback})."
                ),
                allowed_domains=["*"],
                steps=steps
            )

        # Scenario 7C: PC Performance, Memory Optimization & Process Cleanup
        elif any(w in t_lower for w in ["slow", "ram", "clear ram", "clean ram", "free ram", "boost pc", "speed up", "unnecessary processes", "optimize pc", "cleanup pc", "performance", "task manager", "memory"]):
            return ActionPlan(
                task=task,
                reasoning="Autonomous System Operator: Inspect memory consumption, perform Windows working set memory compaction, remove stale cache files, flush DNS resolver, and produce system performance audit report.",
                allowed_domains=["*"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="system_command",
                        intent="Perform safe memory working set compaction, temporary file cleanup, and DNS flush",
                        input_value="optimize_pc",
                        expected_postconditions="System memory compacted and junk cache cleared",
                        verification_method="command_success"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="read_text",
                        intent="Synthesize PC performance and memory audit report",
                        target_locator_strategy="css",
                        target_locator_value="body",
                        verification_method="none"
                    )
                ]
            )

        # Scenario 8: Explicit Google Search vs General Autonomous Web Search (DuckDuckGo)
        elif (
            ("google" in t_lower or any(p in t_lower for p in ["search ", "look up ", "find info", "what is ", "who is ", "latest news", "how to "]))
            and not any(w in t_lower for w in ["wikipedia", "wiki"])
            and not re.search(r"https?://", t_lower)
        ):
            m = re.search(r"(?:search\s+google\s+for|google\s+for|google|search\s+web\s+for|search\s+for|search|look\s+up|find\s+info\s+(?:on|about)|what\s+is|who\s+is)\s+(.+)", task, re.IGNORECASE)
            query = m.group(1).strip(" .?!\"'") if m else norm_task
            encoded_query = urllib.parse.quote_plus(query or norm_task)
            if "google" in t_lower:
                return ActionPlan(
                    task=task,
                    reasoning=f"Search Google for query '{query}' and inspect top search results.",
                    allowed_domains=["google.com", "www.google.com"],
                    steps=[
                        ActionStep(
                            step_id="step_1",
                            action_type="navigate",
                            intent=f"Navigate to Google search for '{query}'",
                            input_value=f"https://www.google.com/search?q={encoded_query}",
                            timeout_ms=10000,
                            expected_postconditions="Google search results loaded",
                            verification_method="url_match",
                            verification_target="google.com/search"
                        ),
                        ActionStep(
                            step_id="step_2",
                            action_type="wait_for_condition",
                            intent="Wait for search results to render",
                            target_locator_value="div#search, #rso",
                            timeout_ms=6000,
                            verification_method="element_present",
                            verification_target="div#search"
                        ),
                        ActionStep(
                            step_id="step_3",
                            action_type="read_text",
                            intent="Read top search result title",
                            target_locator_strategy="css",
                            target_locator_value="div#search h3",
                            timeout_ms=4000,
                            verification_method="none"
                        )
                    ]
                )
            return ActionPlan(
                task=task,
                reasoning=f"Search DuckDuckGo for query '{query}' and inspect top search results.",
                allowed_domains=["duckduckgo.com", "www.duckduckgo.com", "html.duckduckgo.com"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent=f"Search web for '{query}'",
                        input_value=f"https://duckduckgo.com/?q={encoded_query}",
                        timeout_ms=10000,
                        expected_postconditions="Search results page loaded",
                        verification_method="url_match",
                        verification_target="duckduckgo.com"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for search results to render",
                        target_locator_value="[data-testid='result-title-a'], .result__a, h2 a, body",
                        timeout_ms=6000,
                        verification_method="element_present",
                        verification_target="[data-testid='result-title-a'], .result__a, h2 a, body"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="read_text",
                        intent="Read top search result summary",
                        target_locator_strategy="css",
                        target_locator_value="[data-testid='result-title-a'], .result__a, h2 a, body",
                        timeout_ms=4000,
                        verification_method="none"
                    )
                ]
            )

        # Scenario 9: Wikipedia Knowledge Lookup
        elif "wikipedia" in t_lower or "wiki" in t_lower:
            m = re.search(r"(?:wikipedia for|wiki for|search wikipedia for|lookup)\s+([a-zA-Z0-9_\s]+)", task, re.IGNORECASE)
            query = m.group(1).strip() if m else "technology"
            encoded_query = urllib.parse.quote_plus(query)
            return ActionPlan(
                task=task,
                reasoning=f"Look up '{query}' on Wikipedia encyclopedia.",
                allowed_domains=["wikipedia.org", "en.wikipedia.org"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent=f"Navigate to Wikipedia search for '{query}'",
                        input_value=f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}",
                        timeout_ms=10000,
                        expected_postconditions="Wikipedia page loaded",
                        verification_method="url_match",
                        verification_target="wikipedia.org"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for article heading to load",
                        target_locator_value="#firstHeading",
                        timeout_ms=6000,
                        verification_method="element_present",
                        verification_target="#firstHeading"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="read_text",
                        intent="Read article heading",
                        target_locator_strategy="css",
                        target_locator_value="#firstHeading",
                        timeout_ms=4000,
                        verification_method="none"
                    )
                ]
            )

        # Scenario 10: Explicit URL or Bare Domain Navigation (e.g., https://..., github.com, hacker news, reddit)
        elif (
            "http://" in t_lower
            or "https://" in t_lower
            or any(s in t_lower for s in ["hacker news", "hackernews", "reddit", "stackoverflow", "stack overflow", "github"])
            or re.search(r"\b([a-zA-Z0-9-]+\.(?:com|org|net|io|dev|ai|edu|gov|in|co)(?:/[^\s]*)?)\b", t_lower)
        ):
            m_url = re.search(r"(https?://[^\s]+)", task)
            if m_url:
                target_url = m_url.group(1)
                heading_sel = "h1, title, body"
            elif "hacker news" in t_lower or "hackernews" in t_lower:
                target_url = "https://news.ycombinator.com"
                heading_sel = ".titleline a, body"
            elif "reddit" in t_lower:
                sub_m = re.search(r"\br/([a-zA-Z0-9_]+)", task)
                target_url = f"https://www.reddit.com/r/{sub_m.group(1)}" if sub_m else "https://www.reddit.com"
                heading_sel = "h1, shreddit-post, body"
            elif "stackoverflow" in t_lower or "stack overflow" in t_lower:
                target_url = "https://stackoverflow.com"
                heading_sel = "h1, title, body"
            elif "github" in t_lower:
                target_url = "https://github.com/trending"
                heading_sel = "h1, article h2, body"
            else:
                m_dom = re.search(r"\b([a-zA-Z0-9-]+\.(?:com|org|net|io|dev|ai|edu|gov|in|co)(?:/[^\s]*)?)\b", task, re.IGNORECASE)
                raw_dom = m_dom.group(1) if m_dom else "example.com"
                target_url = raw_dom if raw_dom.startswith("http") else f"https://{raw_dom}"
                heading_sel = "h1, title, body"

            domain = urllib.parse.urlparse(target_url).netloc
            return ActionPlan(
                task=task,
                reasoning=f"Navigate to '{target_url}' and inspect target environment.",
                allowed_domains=[domain, domain.replace("www.", "")] if domain else ["*"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent=f"Open target URL: {target_url}",
                        input_value=target_url,
                        timeout_ms=10000,
                        verification_method="url_match",
                        verification_target=domain
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for DOM body to load",
                        target_locator_value="body",
                        timeout_ms=5000,
                        verification_method="none"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="read_text",
                        intent="Read main page heading",
                        target_locator_strategy="css",
                        target_locator_value=heading_sel,
                        timeout_ms=4000,
                        verification_method="none"
                    )
                ]
            )

        # Default fallback plan: fast autonomous web search on DuckDuckGo instead of blind demo page
        if not demo_mode and "demo" not in t_lower and "sandbox" not in t_lower:
            clean_query = re.sub(r"\b(?:open\s+new\s+tab\s+(?:for|of)?|new\s+tab|open)\b", "", norm_task, flags=re.IGNORECASE).strip() or norm_task
            encoded_query = urllib.parse.quote_plus(clean_query)
            return ActionPlan(
                task=task,
                reasoning=f"Autonomous web search & inspection for user task: '{task}'",
                allowed_domains=["duckduckgo.com", "www.duckduckgo.com", "html.duckduckgo.com"],
                steps=[
                    ActionStep(
                        step_id="step_1",
                        action_type="navigate",
                        intent=f"Search web for '{clean_query}'",
                        input_value=f"https://duckduckgo.com/?q={encoded_query}",
                        timeout_ms=10000,
                        expected_postconditions="Search results page loaded",
                        verification_method="url_match",
                        verification_target="duckduckgo.com"
                    ),
                    ActionStep(
                        step_id="step_2",
                        action_type="wait_for_condition",
                        intent="Wait for search results to render",
                        target_locator_value="[data-testid='result-title-a'], .result__a, h2 a, body",
                        timeout_ms=6000,
                        verification_method="none"
                    ),
                    ActionStep(
                        step_id="step_3",
                        action_type="read_text",
                        intent="Inspect top search results",
                        target_locator_strategy="css",
                        target_locator_value="[data-testid='result-title-a'], .result__a, h2 a, body",
                        timeout_ms=4000,
                        verification_method="none"
                    )
                ]
            )

        # Sandbox demo fallback
        return ActionPlan(
            task=task,
            reasoning="Navigate to sandbox target and inspect environment.",
            allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
            steps=[
                ActionStep(
                    step_id="step_1",
                    action_type="navigate",
                    intent=f"Open target address: {base_url}/demo",
                    input_value=f"{base_url}/demo",
                    verification_method="url_match",
                    verification_target=f"{base_url}/demo"
                ),
                ActionStep(
                    step_id="step_2",
                    action_type="read_text",
                    intent="Read sandbox welcome banner",
                    target_locator_strategy="css",
                    target_locator_value="h1",
                    verification_method="none"
                )
            ]
        )

    async def replan_on_failure(
        self,
        task: str,
        failed_step_id: str,
        failure_reason: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None
    ) -> ActionPlan:
        # Create an adaptive recovery plan based on failure context
        return ActionPlan(
            task=f"RECOVERY: {task}",
            reasoning=f"Previous step {failed_step_id} failed with reason: '{failure_reason}'. Replanning alternative locator or action.",
            allowed_domains=allowed_domains or ["127.0.0.1", "localhost"],
            steps=[
                ActionStep(
                    step_id="recovery_step_1",
                    action_type="wait_for_condition",
                    intent="Pause to allow DOM stabilisation and element hydration",
                    timeout_ms=2000,
                    verification_method="none"
                )
            ]
        )
