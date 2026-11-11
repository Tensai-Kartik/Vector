import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { CommandDeck } from './components/CommandDeck';
import { MissionGraph } from './components/MissionGraph';
import { BrowserLab, LocalMediaFileEntry } from './components/BrowserLab';
import { EventStream } from './components/EventStream';
import { ActionInspector } from './components/ActionInspector';
import { AuditReport } from './components/AuditReport';
import { BenchmarkModal } from './components/BenchmarkModal';
import { api } from './services/api';
import { getApiBaseUrl } from './config';
import { MissionSocketClient } from './services/websocket';
import { MissionData, MissionEvent, MissionStepState, ExecutionReport } from './types';
import {
  AUDIO_FILE_REGEX,
  FolderPermissionState,
  clearSavedMediaFolder,
  getSavedMediaFolder,
  isDirectoryPickerSupported,
  isLocalMediaTask,
  queryFolderPermission,
  rankMediaFilesForTask,
  requestFolderPermission,
  saveMediaFolderHandle,
  scanDirectoryMediaFiles,
} from './utils/localFolderStore';

export const App: React.FC = () => {
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [activeMissionId, setActiveMissionId] = useState<string | null>(null);
  const [missionStatus, setMissionStatus] = useState<string>('ready');
  const [steps, setSteps] = useState<MissionStepState[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>();
  const [currentUrl, setCurrentUrl] = useState<string>('about:blank');
  const [screencastFrame, setScreencastFrame] = useState<string | null>(null);
  const [activeActionIntent, setActiveActionIntent] = useState<string | undefined>();
  const [extractedData, setExtractedData] = useState<any[]>([]);
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [report, setReport] = useState<ExecutionReport | undefined>();
  const [approvalRequired, setApprovalRequired] = useState<boolean>(false);
  const [plannerMode, setPlannerMode] = useState<'deterministic' | 'gemini'>('deterministic');
  const [geminiConfigured, setGeminiConfigured] = useState<boolean>(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'waking' | 'online' | 'offline'>('checking');
  const [needsInputAction, setNeedsInputAction] = useState<'local_media_picker' | null>(null);
  const [localMediaFiles, setLocalMediaFiles] = useState<LocalMediaFileEntry[]>([]);
  const [activeLocalMediaIndex, setActiveLocalMediaIndex] = useState<number>(0);
  const [localMediaError, setLocalMediaError] = useState<string | null>(null);
  const [openedInChromeUrl, setOpenedInChromeUrl] = useState<string | null>(null);
  const [authorizedFolderName, setAuthorizedFolderName] = useState<string | null>(null);
  const [authorizedFolderPerm, setAuthorizedFolderPerm] = useState<FolderPermissionState | null>(null);
  const authorizedFolderHandleRef = useRef<FileSystemDirectoryHandle | null>(null);
  const lastLocalTaskRef = useRef<string>('');
  const localMediaUrlsRef = useRef<string[]>([]);
  const localFileInputRef = useRef<HTMLInputElement | null>(null);
  const localDirInputRef = useRef<HTMLInputElement | null>(null);

  const revokeLocalMediaUrls = () => {
    for (const url of localMediaUrlsRef.current) {
      try {
        URL.revokeObjectURL(url);
      } catch {
        // Ignore revoke errors
      }
    }
    localMediaUrlsRef.current = [];
  };

  const loadLocalFileList = (files: File[], folderLabel = 'Downloads', taskHint = ''): string | null => {
    const ranked = rankMediaFilesForTask(files, taskHint);
    if (ranked.length === 0) {
      setLocalMediaError(`No supported video or audio files found in '${folderLabel}'.`);
      return null;
    }
    revokeLocalMediaUrls();
    const items: LocalMediaFileEntry[] = ranked.slice(0, 50).map((f) => ({
      name: f.name,
      url: URL.createObjectURL(f),
      kind: AUDIO_FILE_REGEX.test(f.name) || f.type.startsWith('audio/') ? 'audio' : 'video',
      size: f.size,
    }));
    localMediaUrlsRef.current = items.map((i) => i.url);
    setLocalMediaFiles(items);
    setActiveLocalMediaIndex(0);
    setLocalMediaError(null);
    setNeedsInputAction(null);
    setCurrentUrl(`local://${folderLabel}/${items[0].name}`);
    setMissionStatus('completed');
    setReport((prev) =>
      prev
        ? {
          ...prev,
          verdict: 'success',
          is_verified: true,
          verification_summary: `Playing local media from ${folderLabel}: ${items[0].name}`,
        }
        : prev
    );
    return items[0].name;
  };

  const playFromDirectoryHandle = async (
    dirHandle: FileSystemDirectoryHandle,
    taskHint = ''
  ): Promise<string | null> => {
    const collected = await scanDirectoryMediaFiles(dirHandle);
    return loadLocalFileList(collected, dirHandle.name || 'Media Folder', taskHint);
  };

  const handleAuthorizeMediaFolder = async () => {
    if (!isDirectoryPickerSupported()) {
      localDirInputRef.current?.click();
      return;
    }
    try {
      const dirHandle: FileSystemDirectoryHandle = await (window as any).showDirectoryPicker({
        id: 'vector-media-folder',
        startIn: 'videos',
        mode: 'read',
      });
      await saveMediaFolderHandle(dirHandle);
      authorizedFolderHandleRef.current = dirHandle;
      setAuthorizedFolderName(dirHandle.name || 'Media Folder');
      setAuthorizedFolderPerm('granted');
      await playFromDirectoryHandle(dirHandle, lastLocalTaskRef.current);
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      setLocalMediaError(
        'Chrome blocks folder-level permission on protected folders (Downloads/Desktop/Documents). Pick Videos, Music, or a subfolder (e.g. Downloads/Media), or click "PICK FILES IN DOWNLOADS".'
      );
    }
  };

  const handleUnlockSavedFolder = async () => {
    const handle = authorizedFolderHandleRef.current;
    if (!handle) {
      await handleAuthorizeMediaFolder();
      return;
    }
    const perm = await requestFolderPermission(handle);
    setAuthorizedFolderPerm(perm);
    if (perm === 'granted') {
      await playFromDirectoryHandle(handle, lastLocalTaskRef.current);
    } else {
      setLocalMediaError(`Permission was not granted for '${handle.name}'. Try clicking Change Media Folder.`);
    }
  };

  const handleClearAuthorizedFolder = async () => {
    await clearSavedMediaFolder();
    authorizedFolderHandleRef.current = null;
    setAuthorizedFolderName(null);
    setAuthorizedFolderPerm(null);
  };

  const handlePickLocalMediaFolder = async () => {
    const filePicker = (window as any).showOpenFilePicker;
    if (typeof filePicker !== 'function') {
      localFileInputRef.current?.click();
      return;
    }
    try {
      const handles = await filePicker({
        id: 'vector-downloads-media',
        startIn: 'downloads',
        multiple: true,
        types: [
          {
            description: 'Video & Audio Media',
            accept: {
              'video/*': ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'],
              'audio/*': ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.opus'],
            },
          },
        ],
      });
      const selected: File[] = [];
      for (const h of handles) {
        selected.push(await h.getFile());
      }
      loadLocalFileList(selected, 'Downloads', lastLocalTaskRef.current);
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      localFileInputRef.current?.click();
    }
  };

  const syncSettingsFromBackend = () => {
    api.getSettings().then((s) => {
      setPlannerMode(s.planner_mode === 'gemini' ? 'gemini' : 'deterministic');
      setGeminiConfigured(Boolean(s.gemini_api_key_configured));
    }).catch(() => { });
  };

  useEffect(() => {
    if (backendStatus === 'online') {
      syncSettingsFromBackend();
    }
  }, [backendStatus]);

  // Modals
  const [isBenchmarksOpen, setIsBenchmarksOpen] = useState(false);

  // WebSocket client & poll timer
  const socketClientRef = useRef<MissionSocketClient | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let isMounted = true;
    const startTime = Date.now();

    const checkBackend = async () => {
      try {
        const res = await api.wakeBackend();
        if (isMounted && res && (res.status === 'operational' || res.status === 'pong' || res.active)) {
          setBackendStatus('online');
        }
      } catch (err) {
        if (!isMounted) return;
        const elapsedMs = Date.now() - startTime;
        // If within 60 seconds of initial load, Render may be spinning up from cold sleep (15m idle limit)
        if (elapsedMs < 60000) {
          setBackendStatus('waking');
        } else {
          setBackendStatus('offline');
        }
      }
    };

    // Immediate ping once app is loaded so Render begins waking up while user explores the UI
    checkBackend();

    // Fast poll (every 3.5s) to detect when Render finishes waking up
    const interval = setInterval(checkBackend, 3500);

    // Keepalive Ping: Send lightweight ping every 4 minutes to prevent Render 15-minute auto-sleep
    const keepaliveInterval = setInterval(async () => {
      try {
        await api.ping();
      } catch {
        // Keepalive catch
      }
    }, 4 * 60 * 1000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      clearInterval(keepaliveInterval);
    };
  }, []);

  useEffect(() => {
    socketClientRef.current = new MissionSocketClient();
    getSavedMediaFolder().then(async (saved) => {
      if (!saved) return;
      authorizedFolderHandleRef.current = saved.handle;
      setAuthorizedFolderName(saved.name);
      const perm = await queryFolderPermission(saved.handle);
      setAuthorizedFolderPerm(perm);
    });
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      socketClientRef.current?.disconnectAll();
      revokeLocalMediaUrls();
    };
  }, []);

  const mergeUniqueEvents = (prev: MissionEvent[], incoming: MissionEvent[]) => {
    const map = new Map<string, MissionEvent>();
    for (const ev of prev) {
      map.set(ev.id || `${ev.timestamp}-${ev.event_type}-${ev.message}`, ev);
    }
    for (const ev of incoming) {
      map.set(ev.id || `${ev.timestamp}-${ev.event_type}-${ev.message}`, ev);
    }
    return Array.from(map.values());
  };

  const handleStartMission = async (params: {
    task: string;
    demo_mode: boolean;
    require_approval_for_high_risk: boolean;
    force_execution_method: 'browser' | 'api' | 'auto';
    planner_mode?: 'deterministic' | 'gemini';
    open_browser_window?: boolean;
    chrome_target_mode?: 'tab' | 'window';
  }) => {
    // Clean up any previous mission listeners/timers
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    socketClientRef.current?.disconnectAll();

    // Reset state for new mission
    revokeLocalMediaUrls();
    setLocalMediaFiles([]);
    setActiveLocalMediaIndex(0);
    setLocalMediaError(null);
    setNeedsInputAction(null);
    setOpenedInChromeUrl(null);
    setScreencastFrame(null);
    setSteps([]);
    setEvents([]);
    setReport(undefined);
    setExtractedData([]);
    setArtifacts([]);
    setSelectedStepId(undefined);
    setActiveActionIntent(undefined);
    setApprovalRequired(false);
    setMissionStatus('queued');

    if (backendStatus === 'waking') {
      alert("⏳ Render Cloud Backend is currently waking up from idle sleep.\n\nRender free containers spin down after 15 minutes of inactivity and take ~25-40 seconds to warm up.\nPlease wait a moment until the status pill turns green (BACKEND ONLINE), then launch your mission!");
      setMissionStatus('ready');
      return;
    }

    if (backendStatus === 'offline') {
      alert("⚠️ Vector Backend is not running!\n\nPlease start the backend server in your terminal:\n  python -m uvicorn backend.app.main:app --reload\n(or double-click start_vector.bat)");
      setMissionStatus('failed');
      return;
    }

    const isCloudBackend = !/localhost|127\.0\.0\.1/i.test(getApiBaseUrl());
    const localMediaRequested = isLocalMediaTask(params.task);
    if (localMediaRequested) {
      lastLocalTaskRef.current = params.task;
    }
    const isLocalOrSystemPrompt =
      localMediaRequested ||
      (/\b(downloads?|folder|drive|clear\s*ram|clean\s*ram|optimize\s*pc|invoice|procurement|requisition|sandbox|benchmark|demo|github\s*api)\b/i.test(params.task) &&
        !/youtube/i.test(params.task));

    // Open a real Chrome tab or window synchronously in the click gesture when running in cloud mode
    let pendingChromeWin: Window | null = null;
    if (isCloudBackend && params.open_browser_window && !isLocalOrSystemPrompt) {
      const targetName = params.chrome_target_mode === 'window' ? `vector_win_${Date.now()}` : '_blank';
      const windowFeatures =
        params.chrome_target_mode === 'window'
          ? 'width=1280,height=820,left=60,top=40,toolbar=yes,location=yes,menubar=yes,status=yes,resizable=yes,scrollbars=yes'
          : undefined;
      pendingChromeWin = window.open('about:blank', targetName, windowFeatures);
      if (pendingChromeWin) {
        try {
          pendingChromeWin.document.write(
            '<html><head><title>VECTOR — Resolving Target</title></head><body style="background:#080c13;color:#e2e8f0;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;"><div style="text-align:center;"><div style="color:#d4ff00;font-size:18px;font-weight:bold;margin-bottom:8px;">VECTOR AUTONOMOUS OPERATOR</div><div style="font-size:13px;opacity:0.8;">Resolving destination in your Chrome session...</div></div></body></html>'
          );
          pendingChromeWin.document.close();
        } catch {
          // Ignore cross-origin/document write restrictions
        }
      }
    }

    try {
      let clientHandledUrl: string | undefined;

      // Option A: If an authorized local media folder handle is saved in IndexedDB, scan & auto-play without any file picker
      const savedFolder = authorizedFolderHandleRef.current;
      if (isCloudBackend && localMediaRequested && savedFolder) {
        let perm = await queryFolderPermission(savedFolder);
        if (perm === 'prompt') {
          perm = await requestFolderPermission(savedFolder);
        }
        setAuthorizedFolderPerm(perm);
        if (perm === 'granted') {
          const autoPlayedName = await playFromDirectoryHandle(savedFolder, params.task);
          if (autoPlayedName) {
            clientHandledUrl = `local://${savedFolder.name || 'Media Folder'}/${autoPlayedName}`;
          }
        }
      }

      if (!clientHandledUrl && isCloudBackend && params.open_browser_window && !isLocalOrSystemPrompt) {
        const launchMeta = await api.resolveLaunch(params.task).catch(() => ({ should_open_tab: false } as any));
        if (launchMeta?.should_open_tab && launchMeta.launch_url) {
          setOpenedInChromeUrl(launchMeta.launch_url);
          setCurrentUrl(launchMeta.launch_url);
          if (pendingChromeWin && !pendingChromeWin.closed) {
            pendingChromeWin.location.replace(launchMeta.launch_url);
            pendingChromeWin.focus();
            if (launchMeta.direct_tab_sufficient) {
              clientHandledUrl = launchMeta.launch_url;
            }
          }
        } else if (pendingChromeWin && !pendingChromeWin.closed) {
          pendingChromeWin.close();
          pendingChromeWin = null;
        }
      } else if (pendingChromeWin && !pendingChromeWin.closed) {
        pendingChromeWin.close();
        pendingChromeWin = null;
      }

      const res = await api.createMission({
        task: params.task,
        demo_mode: params.demo_mode,
        require_approval_for_high_risk: params.require_approval_for_high_risk,
        force_execution_method: params.force_execution_method,
        planner_mode: params.planner_mode || plannerMode,
        open_browser_window: params.open_browser_window,
        client_handled_url: clientHandledUrl,
      });

      const mId = res.mission_id;
      setActiveMissionId(mId);

      // Connect WebSockets for events & screencast stream
      socketClientRef.current?.connectEvents(mId, (event: MissionEvent) => {
        setEvents((prev) => mergeUniqueEvents(prev, [event]));

        if (event.event_type === 'plan_generated' && event.details?.steps) {
          const parsedSteps = event.details.steps.map((s: any) => ({
            step_id: s.step_id,
            action_type: s.action_type,
            intent: s.intent,
            target_description: s.target_description,
            target_locator_value: s.target_locator_value,
            input_value: s.input_value,
            status: 'pending',
          }));
          setSteps(parsedSteps);
          setMissionStatus('running');

          const firstNav = event.details.steps.find((s: any) => s.action_type === 'navigate');
          if (firstNav?.input_value) {
            setCurrentUrl(firstNav.input_value);
          }
        }

        if (event.event_type === 'browser_action_started') {
          setActiveActionIntent(event.message);
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id ? { ...s, status: 'running' } : s
              )
            );
            setSelectedStepId(event.step_id);
          }
        }

        if (event.event_type === 'browser_action_completed') {
          if (event.details?.final_url) {
            setCurrentUrl(event.details.final_url);
          }
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id
                  ? {
                    ...s,
                    status: 'completed',
                    verification_status: 'passed',
                    verification_evidence: event.details?.evidence,
                  }
                  : s
              )
            );
          }
        }

        if (event.event_type === 'step_rejected') {
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id
                  ? {
                    ...s,
                    status: 'rejected',
                    validation_message: event.details?.error,
                  }
                  : s
              )
            );
          }
        }

        if (event.event_type === 'approval_requested') {
          setApprovalRequired(true);
          setMissionStatus('awaiting_approval');
        }

        if (event.event_type === 'approval_granted') {
          setApprovalRequired(false);
          setMissionStatus('running');
        }

        if (event.event_type === 'artifact_created' && event.details) {
          setArtifacts((prev) => [...prev, event.details]);
        }

        if (event.event_type === 'replanning_occurred' && Array.isArray(event.details?.steps) && event.details.steps.length > 0) {
          const recSteps: MissionStepState[] = event.details.steps.map((s: any) => ({
            step_id: s.step_id,
            action_type: s.action_type,
            intent: s.intent,
            target_description: s.target_description,
            target_locator_value: s.target_locator_value,
            input_value: s.input_value,
            status: 'pending',
            retry_count: 0,
          }));
          setSteps((prev) => {
            const kept = event.details?.replaced_tail
              ? prev
                .filter((p) => p.status === 'completed' || p.status === 'skipped' || p.status === 'failed' || p.status === 'rejected' || p.step_id === event.step_id)
                .map((p) => (p.step_id === event.step_id ? { ...p, status: 'skipped' as const } : p))
              : prev;
            return [...kept, ...recSteps];
          });
        }

        if (event.event_type === 'verification_failed' || event.event_type === 'needs_input') {
          if (event.details?.final_url) {
            setCurrentUrl(event.details.final_url);
          }
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id
                  ? {
                    ...s,
                    status: 'failed',
                    error_message: event.message,
                  }
                  : s
              )
            );
          }
          if (event.event_type === 'needs_input') {
            setMissionStatus('needs_input');
            setActiveActionIntent(undefined);
            if (event.details?.action_required === 'local_media_picker') {
              setNeedsInputAction('local_media_picker');
            }
            if (event.details && (event.details.total_steps !== undefined || event.details.verdict)) {
              setReport(event.details as any as ExecutionReport);
              if (event.details.extracted_records) {
                setExtractedData(event.details.extracted_records);
              }
            }
          }
        }

        if (event.event_type === 'mission_completed' || event.event_type === 'mission_failed') {
          if (!event.details?.captcha_blocked) {
            setMissionStatus(event.event_type === 'mission_completed' ? 'completed' : 'failed');
          }
          setActiveActionIntent(undefined);
          if (event.details && (event.details.total_steps !== undefined || event.details.verdict)) {
            setReport(event.details as any as ExecutionReport);
            if (event.details.extracted_records) {
              setExtractedData(event.details.extracted_records);
            }
          }
        }
      });

      socketClientRef.current?.connectStream(mId, (b64Img: string) => {
        setScreencastFrame(b64Img);
      });

      // Poll mission state periodically if active
      let consecutiveErrors = 0;
      pollIntervalRef.current = setInterval(async () => {
        if (!mId) return;
        try {
          const m = await api.getMission(mId);
          consecutiveErrors = 0;

          if (m.status === 'awaiting_approval') {
            setMissionStatus('awaiting_approval');
            setApprovalRequired(true);
          } else if (m.status) {
            setMissionStatus(m.status as any);
          }

          // Fallback event syncing if WebSockets are dropped or blocked by network proxies
          if (m.events && Array.isArray(m.events) && m.events.length > 0) {
            setEvents((prev) => mergeUniqueEvents(prev, m.events));
          }

          if ((m as any).current_url) {
            setCurrentUrl((m as any).current_url);
          } else if (m.steps && m.steps.length > 0) {
            const activeStep = m.steps.find((s: any) => s.status === 'running') || m.steps[m.steps.length - 1];
            if (activeStep?.input_value && (activeStep.action_type === 'navigate' || activeStep.action_type === 'launch_app')) {
              setCurrentUrl(activeStep.input_value);
            }
          }

          if (m.steps && m.steps.length > 0) {
            setSteps(m.steps);
          }
          if (m.status === 'completed' || m.status === 'failed' || m.status === 'cancelled' || m.status === 'needs_input') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setMissionStatus(m.status);
            setActiveActionIntent(undefined);
            setApprovalRequired(false);
            if ((m as any).needs_input_action === 'local_media_picker') {
              setNeedsInputAction('local_media_picker');
            }
            if (m.summary_report && (m.summary_report.total_steps !== undefined || m.summary_report.verdict)) {
              setReport(m.summary_report);
              setExtractedData(m.extracted_data || []);
              setArtifacts(m.artifacts || []);
            }
          }
        } catch (e) {
          consecutiveErrors += 1;
          if (consecutiveErrors >= 8) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          }
        }
      }, 1200);
    } catch (err) {
      console.error('Mission launch failed', err);
      setMissionStatus('failed');
      setBackendStatus('offline');
    }
  };

  const handleApproveStep = async () => {
    if (!activeMissionId) return;
    try {
      await api.approveMission(activeMissionId);
      setApprovalRequired(false);
    } catch (err) {
      console.error('Approval failed', err);
    }
  };

  const handleCancelMission = async () => {
    revokeLocalMediaUrls();
    setLocalMediaFiles([]);
    setNeedsInputAction(null);
    try {
      if (activeMissionId) {
        await api.cancelMission(activeMissionId);
      } else {
        await api.killAllMissions();
      }
      setMissionStatus('cancelled');
      setActiveActionIntent(undefined);
    } catch (err) {
      console.error('Cancellation failed', err);
    }
  };

  const selectedStep = steps.find(
    (s) => s.step_id === selectedStepId || ('step-' + s.step_id) === selectedStepId || s.step_id === selectedStepId?.replace(/^step-/, '')
  );

  const needsInputEvent = [...events].reverse().find((e) => e.event_type === 'needs_input');
  const needsInputReason =
    needsInputEvent?.message || (missionStatus === 'needs_input' ? report?.verification_summary : undefined);
  const resolvedNeedsInputAction: 'local_media_picker' | null =
    missionStatus === 'needs_input'
      ? needsInputAction ||
      (needsInputEvent?.details?.action_required === 'local_media_picker' ? 'local_media_picker' : null)
      : null;

  return (
      <div className="min-h-screen bg-vector-darkest text-slate-100 flex flex-col bg-grid-pattern overflow-x-hidden">
        <input
          ref={localFileInputRef}
          type="file"
          multiple
          accept="video/*,audio/*,.mkv,.mp4,.webm,.avi,.mov,.mp3,.m4a,.wav,.flac"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              loadLocalFileList(Array.from(e.target.files), 'Downloads', lastLocalTaskRef.current);
            }
            e.target.value = '';
          }}
        />
        <input
          ref={localDirInputRef}
          type="file"
          multiple
          {...({ webkitdirectory: '' } as any)}
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              loadLocalFileList(Array.from(e.target.files), 'Selected Folder', lastLocalTaskRef.current);
            }
            e.target.value = '';
          }}
        />
        <Header
          demoMode={demoMode}
          setDemoMode={setDemoMode}
          onOpenBenchmarks={() => setIsBenchmarksOpen(true)}
          missionStatus={missionStatus}
          onKillMission={handleCancelMission}
          activeMissionId={activeMissionId}
          backendStatus={backendStatus}
        />

        <main className="flex-1 p-3 sm:p-6 space-y-4 sm:space-y-6 max-w-[1700px] mx-auto w-full">
          {/* Command Deck */}
          <CommandDeck
            onStartMission={handleStartMission}
            onApproveStep={handleApproveStep}
            onCancelMission={handleCancelMission}
            missionStatus={missionStatus}
            demoMode={demoMode}
            approvalRequired={approvalRequired}
            needsInputReason={needsInputReason}
            needsInputAction={resolvedNeedsInputAction}
            authorizedFolderName={authorizedFolderName}
            authorizedFolderPerm={authorizedFolderPerm}
            onAuthorizeMediaFolder={handleAuthorizeMediaFolder}
            onUnlockSavedFolder={handleUnlockSavedFolder}
            onPickLocalMediaFolder={handlePickLocalMediaFolder}
            currentUrl={currentUrl}
            plannerMode={plannerMode}
            onChangePlannerMode={setPlannerMode}
            geminiConfigured={geminiConfigured}
            backendStatus={backendStatus}
          />

          {/* Primary Operational Workspace Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Left Column: Mission Execution Graph */}
            <div className="space-y-4 sm:space-y-6 flex flex-col min-w-0">
              <MissionGraph
                steps={steps}
                selectedStepId={selectedStepId}
                onSelectStep={(id) => setSelectedStepId(id)}
                missionStatus={missionStatus}
              />
              <ActionInspector step={selectedStep} />
            </div>

            {/* Right Column: Live Browser Lab Screencast & Event Stream */}
            <div className="space-y-4 sm:space-y-6 flex flex-col min-w-0">
              <BrowserLab
                currentUrl={currentUrl}
                screencastFrame={screencastFrame}
                activeAction={activeActionIntent}
                isConnected={true}
                isStreaming={missionStatus === 'running'}
                onKill={handleCancelMission}
                localMediaFiles={localMediaFiles}
                activeLocalMediaIndex={activeLocalMediaIndex}
                onSelectLocalMediaIndex={(idx) => {
                  setActiveLocalMediaIndex(idx);
                  if (localMediaFiles[idx]) {
                    setCurrentUrl(
                      `local://${authorizedFolderName || 'Local Media'}/${localMediaFiles[idx].name}`
                    );
                  }
                }}
                needsLocalFolderPicker={resolvedNeedsInputAction === 'local_media_picker'}
                authorizedFolderName={authorizedFolderName}
                authorizedFolderPerm={authorizedFolderPerm}
                onAuthorizeMediaFolder={handleAuthorizeMediaFolder}
                onUnlockSavedFolder={handleUnlockSavedFolder}
                onClearAuthorizedFolder={handleClearAuthorizedFolder}
                onPickLocalMediaFolder={handlePickLocalMediaFolder}
                onSelectLocalFiles={(fileList) =>
                  loadLocalFileList(Array.from(fileList), 'Selected Files', lastLocalTaskRef.current)
                }
                localMediaError={localMediaError}
                openedInChromeUrl={openedInChromeUrl}
              />
              <EventStream events={events} />
            </div>
          </div>

          {/* Bottom Area: Final Verification & Audit Dossier */}
          <AuditReport
            report={report}
            extractedData={extractedData}
            artifacts={artifacts}
            missionId={activeMissionId || undefined}
          />
        </main>

        {/* Benchmark 20 Suite Modal */}
        <BenchmarkModal isOpen={isBenchmarksOpen} onClose={() => setIsBenchmarksOpen(false)} />
      </div>
      );
};

      export default App;
