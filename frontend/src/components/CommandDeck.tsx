import React, { useState } from 'react';
import { Play, Shield, XCircle, Monitor } from 'lucide-react';

interface CommandDeckProps {
  onStartMission: (params: {
    task: string;
    demo_mode: boolean;
    require_approval_for_high_risk: boolean;
    force_execution_method: 'browser' | 'api' | 'auto';
    open_browser_window?: boolean;
  }) => void;
  onApproveStep: () => void;
  onCancelMission: () => void;
  missionStatus?: string;
  demoMode: boolean;
  approvalRequired?: boolean;
}

const SMART_SUGGESTIONS = [
  {
    icon: '▶',
    label: 'CarryMinati YouTube',
    task: 'open youtube and play latest video of carryminati',
  },
  {
    icon: '⚡',
    label: 'GitHub API (Octocat)',
    task: 'Query GitHub repository metadata for octocat/Hello-World using authorized REST API adapter.',
  },
  {
    icon: '📄',
    label: 'Download Invoice CSV',
    task: 'Open authorized accounts portal, locate latest invoice INV-2026-004, inspect detail page, and download the verified CSV file.',
  },
  {
    icon: '📁',
    label: 'Play Downloads Media',
    task: 'open downloads and play first media',
  },
  {
    icon: '🎬',
    label: 'D: Drive Movies',
    task: 'open d drive and play video in movies',
  },
  {
    icon: '💬',
    label: 'WhatsApp',
    task: 'open whatsapp',
  },
  {
    icon: '🎮',
    label: 'Epic Games',
    task: 'open epic games home',
  },
  {
    icon: '⚡',
    label: 'Clear RAM & Optimize PC',
    task: 'my pc is slow please clear extra ram and stop unnecessary processes',
  },
  {
    icon: '🔍',
    label: 'Google AI Search',
    task: 'Search Google for latest autonomous AI agent benchmarks and inspect top results.',
  },
  {
    icon: '📝',
    label: 'Procurement Approval',
    task: 'Open procurement requisition form, fill vendor and amount fields, certify compliance, request approval, and submit.',
  },
];

export const CommandDeck: React.FC<CommandDeckProps> = ({
  onStartMission,
  onApproveStep,
  onCancelMission,
  missionStatus = 'ready',
  demoMode,
  approvalRequired = false,
}) => {
  const [task, setTask] = useState('open youtube and play latest video of carryminati');
  const [requireApproval, setRequireApproval] = useState(false);
  const [openBrowserWindow, setOpenBrowserWindow] = useState(true);

  const isRunning =
    missionStatus === 'running' ||
    missionStatus === 'planning' ||
    missionStatus === 'inspecting' ||
    missionStatus === 'awaiting_approval';

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
      open_browser_window: openBrowserWindow,
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
            placeholder="Type a web or API mission in natural language (e.g. 'open youtube and play latest video of carryminati', 'download invoice', etc.)..."
            className="w-full bg-[#080c13] border border-white/10 rounded-xl p-3 sm:p-3.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 font-sans focus:outline-none focus:border-[#d4ff00]/80 focus:ring-1 focus:ring-[#d4ff00]/40 transition resize-none disabled:opacity-60"
          />
          <div className="absolute right-3 bottom-3 text-[10px] font-mono text-slate-500 pointer-events-none hidden sm:block">
            Ctrl + Enter
          </div>
        </div>

        {/* Curated Suggestion Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1.5 scrollbar-none touch-pan-x">
          <span className="text-[10px] font-mono text-slate-400 shrink-0 uppercase tracking-wider mr-1">
            EXAMPLES:
          </span>
          {SMART_SUGGESTIONS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isRunning}
              onClick={() => setTask(preset.task)}
              className={`text-[11px] sm:text-xs px-2.5 py-1 rounded-lg border font-mono transition text-left flex items-center space-x-1.5 shrink-0 ${
                task === preset.task
                  ? 'bg-[#d4ff00]/15 border-[#d4ff00]/50 text-[#d4ff00] font-semibold'
                  : 'bg-white/5 border-white/5 text-slate-300 hover:border-white/20 hover:text-white'
              }`}
            >
              <span>{preset.icon}</span>
              <span className="whitespace-nowrap">{preset.label}</span>
            </button>
          ))}
        </div>

        {/* Operational Controls & Launch Bar */}
        <div className="pt-2 border-t border-white/5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            {/* Visible Browser Window Toggle */}
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
                <span>Visible Window</span>
              </span>
            </label>

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
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
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
                className="w-full sm:w-auto justify-center px-4 py-2 rounded-xl bg-rose-950/80 hover:bg-rose-900 border border-rose-700/50 text-rose-300 font-mono text-xs font-semibold flex items-center space-x-1.5 transition active:scale-95"
              >
                <XCircle className="w-4 h-4" />
                <span>ABORT</span>
              </button>
            ) : (
              <button
                type="submit"
                className="w-full sm:w-auto justify-center px-5 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg shadow-[#d4ff00]/10 transition active:scale-95"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>LAUNCH MISSION</span>
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};

export default CommandDeck;
