import React, { useState } from 'react';
import { Play, Shield, Monitor, OctagonAlert, Cpu, FolderOpen } from 'lucide-react';

interface CommandDeckProps {
  onStartMission: (params: {
    task: string;
    demo_mode: boolean;
    require_approval_for_high_risk: boolean;
    force_execution_method: 'browser' | 'api' | 'auto';
    planner_mode?: 'deterministic' | 'gemini';
    open_browser_window?: boolean;
    chrome_target_mode?: 'tab' | 'window';
  }) => void;
  onApproveStep: () => void;
  onCancelMission: () => void;
  missionStatus?: string;
  demoMode: boolean;
  approvalRequired?: boolean;
  needsInputReason?: string;
  needsInputAction?: 'local_media_picker' | null;
  onPickLocalMediaFolder?: () => void;
  currentUrl?: string;
  plannerMode?: 'deterministic' | 'gemini';
  onChangePlannerMode?: (mode: 'deterministic' | 'gemini') => void;
  geminiConfigured?: boolean;
  backendStatus?: 'checking' | 'waking' | 'online' | 'offline';
}

export const CommandDeck: React.FC<CommandDeckProps> = ({
  onStartMission,
  onApproveStep,
  onCancelMission,
  missionStatus = 'ready',
  demoMode,
  approvalRequired = false,
  needsInputReason,
  needsInputAction = null,
  onPickLocalMediaFolder,
  currentUrl,
  plannerMode = 'deterministic',
  onChangePlannerMode,
  geminiConfigured = false,
  backendStatus = 'checking',
}) => {
  const [task, setTask] = useState('');
  const [requireApproval, setRequireApproval] = useState(false);
  const [openBrowserWindow, setOpenBrowserWindow] = useState(true);
  const [chromeTargetMode, setChromeTargetMode] = useState<'tab' | 'window'>('tab');

  const isRunning =
    missionStatus === 'running' ||
    missionStatus === 'planning' ||
    missionStatus === 'inspecting' ||
    missionStatus === 'awaiting_approval' ||
    missionStatus === 'queued';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim()) return;

    const isSyntheticDemo = /invoice|procurement|requisition|fleet|phantom|injection|sandbox|synthetic/i.test(task);
    const effectiveDemoMode = isSyntheticDemo && demoMode;

    onStartMission({
      task: task.trim(),
      demo_mode: effectiveDemoMode,
      require_approval_for_high_risk: requireApproval,
      force_execution_method: 'auto',
      planner_mode: plannerMode,
      open_browser_window: openBrowserWindow,
      chrome_target_mode: chromeTargetMode,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit(e);
    }
  };

  return (
    <div className="bg-[#0b0f17] border border-white/10 rounded-2xl p-4 sm:p-5 shadow-2xl relative overflow-hidden transition-all">
      {/* Subtle Ambient Background Accent */}
      <div className="absolute top-0 right-0 w-72 h-20 bg-[#d4ff00]/5 blur-3xl pointer-events-none" />

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 sm:gap-2 mb-3">
        <div className="flex items-center space-x-2">
          <img src="/logo_bg.png" alt="VECTOR" className="w-4 h-4 object-contain drop-shadow-[0_0_6px_rgba(212,255,0,0.3)] shrink-0" />
          <h2 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider truncate">
            VECTOR Autonomous Mission Control
          </h2>
        </div>
        <div className="flex items-center space-x-2 text-[10px] font-mono text-slate-400">
          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/5 truncate hidden sm:inline-block">
            HYBRID ROUTER · API FIRST + PLAYWRIGHT FALLBACK
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Natural Language Prompt Area */}
        <div className="relative">
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isRunning}
            rows={2}
            placeholder="Type a web or API mission in natural language (e.g. 'Search for latest AI agent research and extract findings', 'Download invoice report')..."
            className="w-full bg-[#080c13] border border-white/10 rounded-xl p-3 sm:p-3.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 font-sans focus:outline-none focus:border-[#d4ff00]/80 focus:ring-1 focus:ring-[#d4ff00]/40 transition resize-none disabled:opacity-60"
          />
          <div className="absolute right-3 bottom-3 text-[10px] font-mono text-slate-500 pointer-events-none hidden sm:block">
            Ctrl + Enter
          </div>
        </div>

        {/* Waking Render Cloud Banner */}
        {backendStatus === 'waking' && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center justify-between gap-2 animate-pulse">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping shrink-0" />
              <span>
                <strong>Waking Render Cloud Backend:</strong> Render spins down free containers after 15m idle. Initializing cloud instance (~25-40s). You can compose your task while it connects.
              </span>
            </div>
          </div>
        )}

        {/* Offline Warning Banner */}
        {backendStatus === 'offline' && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono flex items-center justify-between gap-2 animate-pulse">
            <div className="flex items-center space-x-2">
              <OctagonAlert className="w-4 h-4 text-rose-400 shrink-0" />
              <span>
                <strong>Vector Backend is not running!</strong> Please start the backend in terminal: <code className="bg-black/50 px-1.5 py-0.5 rounded text-white font-mono">python -m uvicorn backend.app.main:app --reload</code>
              </span>
            </div>
          </div>
        )}

        {/* Operational Controls & Launch Bar */}
        <div className="pt-2 border-t border-white/5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            {/* Visible Browser Window / Chrome Tab Toggle */}
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-2 text-xs font-mono text-slate-300 cursor-pointer select-none py-0.5">
                <input
                  type="checkbox"
                  checked={openBrowserWindow}
                  onChange={(e) => setOpenBrowserWindow(e.target.checked)}
                  disabled={isRunning}
                  className="rounded bg-black border-white/20 text-[#d4ff00] focus:ring-[#d4ff00] h-3.5 w-3.5 cursor-pointer"
                />
                <span className="flex items-center space-x-1.5">
                  <Monitor className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span>Open in Chrome</span>
                </span>
              </label>

              {openBrowserWindow && (
                <div className="flex items-center rounded-lg bg-[#080c13] border border-white/10 p-0.5 text-[10px] font-mono">
                  <button
                    type="button"
                    disabled={isRunning}
                    onClick={() => setChromeTargetMode('tab')}
                    className={`px-1.5 py-0.5 rounded transition ${
                      chromeTargetMode === 'tab'
                        ? 'bg-cyan-400 text-black font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                    title="Open target URL in a new Chrome tab using your logins & history"
                  >
                    New Tab
                  </button>
                  <button
                    type="button"
                    disabled={isRunning}
                    onClick={() => setChromeTargetMode('window')}
                    className={`px-1.5 py-0.5 rounded transition ${
                      chromeTargetMode === 'window'
                        ? 'bg-cyan-400 text-black font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                    title="Open target URL in a new Chrome window"
                  >
                    New Window
                  </button>
                </div>
              )}
            </div>

            {/* Approval Gate Toggle */}
            <label className="flex items-center space-x-2 text-xs font-mono text-slate-300 cursor-pointer select-none py-0.5">
              <input
                type="checkbox"
                checked={requireApproval}
                onChange={(e) => setRequireApproval(e.target.checked)}
                disabled={isRunning}
                className="rounded bg-black border-white/20 text-[#d4ff00] focus:ring-[#d4ff00] h-3.5 w-3.5 cursor-pointer"
              />
              <span className="flex items-center space-x-1.5">
                <Shield className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span>Approval on High Risk</span>
              </span>
            </label>

            {/* Planner Engine Selector */}
            <div
              className="flex items-center rounded-lg bg-[#080c13] border border-white/10 p-0.5 text-[10px] font-mono"
              title={
                geminiConfigured
                  ? 'Default: Deterministic Planner (Gemini LLM standby fallback ready)'
                  : 'Default: Deterministic Planner (configure Gemini API key in Settings for LLM fallback)'
              }
            >
              <Cpu className="w-3 h-3 text-[#d4ff00] mx-1.5 shrink-0" />
              <button
                type="button"
                disabled={isRunning}
                onClick={() => onChangePlannerMode?.('deterministic')}
                className={`px-2 py-0.5 rounded-md transition ${
                  plannerMode === 'deterministic'
                    ? 'bg-[#d4ff00] text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Deterministic
              </button>
              <button
                type="button"
                disabled={isRunning}
                onClick={() => onChangePlannerMode?.('gemini')}
                className={`px-2 py-0.5 rounded-md transition ${
                  plannerMode === 'gemini'
                    ? 'bg-cyan-400 text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Gemini LLM
              </button>
            </div>
          </div>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full sm:w-auto justify-end">
            {missionStatus === 'needs_input' && (
              needsInputAction === 'local_media_picker' && onPickLocalMediaFolder ? (
                <div className="flex items-center space-x-2 bg-cyan-500/10 border border-cyan-500/30 px-2.5 sm:px-3 py-1.5 rounded-xl">
                  <FolderOpen className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span className="text-[10px] sm:text-[11px] font-mono text-cyan-200 max-w-md">
                    {needsInputReason || 'Grant browser folder permission to open Downloads and play local media.'}
                  </span>
                  <button
                    type="button"
                    onClick={onPickLocalMediaFolder}
                    className="px-2.5 py-1 rounded-lg bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-[10px] font-bold shrink-0 transition cursor-pointer"
                  >
                    SELECT MEDIA IN DOWNLOADS
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-2.5 sm:px-3 py-1.5 rounded-xl">
                  <Shield className="w-4 h-4 text-amber-400 shrink-0" />
                  <span className="text-[10px] sm:text-[11px] font-mono text-amber-200 max-w-md">
                    {needsInputReason || 'Human verification (CAPTCHA) required on target site.'}
                  </span>
                  {currentUrl && currentUrl.startsWith('http') && (
                    <a
                      href={currentUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1 rounded-lg bg-amber-400 hover:bg-amber-300 text-black font-mono text-[10px] font-bold shrink-0 transition"
                    >
                      OPEN TAB
                    </a>
                  )}
                </div>
              )
            )}

            {approvalRequired && (
              <div className="flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-2.5 sm:px-3 py-1.5 rounded-xl shrink-0">
                <Shield className="w-4 h-4 text-amber-400 animate-pulse shrink-0" />
                <span className="text-[10px] sm:text-[11px] font-mono font-medium text-amber-300 hidden xs:inline sm:inline">
                  Permission Required
                </span>
                <button
                  type="button"
                  onClick={onApproveStep}
                  className="px-3 sm:px-3.5 py-1.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-black font-mono text-xs font-bold flex items-center space-x-1.5 shadow-md shadow-amber-500/20 transition active:scale-95"
                >
                  <span>AUTHORIZE</span>
                </button>
              </div>
            )}

            {isRunning ? (
              <button
                type="button"
                onClick={onCancelMission}
                className="w-full sm:w-auto justify-center px-4 py-2 rounded-xl bg-rose-900/90 hover:bg-rose-800 border border-rose-500/50 text-white font-mono text-xs font-bold flex items-center space-x-1.5 transition active:scale-95 shadow-lg shadow-rose-950/40"
                title="Immediately abort active mission and terminate browser session"
              >
                <OctagonAlert className="w-4 h-4 text-rose-300 animate-pulse" />
                <span>KILL MISSION</span>
              </button>
            ) : (
              <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full sm:w-auto">
                {missionStatus !== 'ready' && (
                  <button
                    type="button"
                    onClick={onCancelMission}
                    className="flex-1 sm:flex-none justify-center px-3 sm:px-3.5 py-2 rounded-xl bg-rose-950/60 hover:bg-rose-900 border border-rose-500/30 text-rose-300 hover:text-white font-mono text-xs font-bold flex items-center space-x-1.5 transition active:scale-95 shadow-md"
                    title="Force close browser and stop background processes"
                  >
                    <OctagonAlert className="w-3.5 h-3.5 text-rose-400" />
                    <span>KILL BROWSER</span>
                  </button>
                )}
                <button
                  type="submit"
                  className="flex-1 sm:flex-none justify-center px-5 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg shadow-[#d4ff00]/10 transition active:scale-95"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>LAUNCH MISSION</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};

export default CommandDeck;
