import React from 'react';
import { ShieldCheck, Sliders } from 'lucide-react';

interface HeaderProps {
  demoMode: boolean;
  setDemoMode: (val: boolean) => void;
  onOpenSettings: () => void;
  onOpenBenchmarks: () => void;
  missionStatus?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSettings,
  onOpenBenchmarks,
  missionStatus = 'ready',
}) => {
  return (
    <header className="border-b border-white/10 bg-[#07090e]/95 backdrop-blur-xl px-3 sm:px-6 py-2.5 sm:py-3.5 flex items-center justify-between sticky top-0 z-40 transition-all">
      {/* Brand & Mission Status */}
      <div className="flex items-center space-x-2.5 sm:space-x-4 min-w-0">
        <div className="flex items-center space-x-2.5 sm:space-x-3 shrink-0">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-tr from-[#d4ff00]/20 to-[#d4ff00]/5 border border-[#d4ff00]/40 flex items-center justify-center shadow-lg shadow-[#d4ff00]/15 p-1 transition hover:border-[#d4ff00]/70 shrink-0">
            <img src="/logo_bg.png" alt="VECTOR Logo" className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(212,255,0,0.35)]" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-1.5 sm:space-x-2">
              <span className="font-bold text-white tracking-wider text-sm font-mono">VECTOR</span>
              <span className="text-[9px] font-mono font-bold px-1.5 sm:px-2 py-0.5 rounded-full bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30 tracking-widest">
                v1.0
              </span>
            </div>
            <p className="text-[9px] sm:text-[10px] text-slate-400 font-mono leading-none mt-0.5 truncate hidden xs:block sm:block">
              Autonomous Web Operator · Hybrid API + Playwright
            </p>
          </div>
        </div>

        <div className="h-5 w-px bg-white/10 hidden md:block" />

        {/* Dynamic Status Pill */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 bg-white/5 px-2 sm:px-3 py-1 rounded-full border border-white/10 text-[10px] sm:text-xs font-mono shrink-0">
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              missionStatus === 'running'
                ? 'bg-[#d4ff00] animate-ping'
                : missionStatus === 'awaiting_approval'
                ? 'bg-amber-400 animate-pulse'
                : missionStatus === 'completed'
                ? 'bg-emerald-400'
                : missionStatus === 'failed'
                ? 'bg-rose-400'
                : 'bg-cyan-400'
            }`}
          />
          <span className="text-slate-300 uppercase tracking-wider text-[9px] sm:text-[10px]">
            <span className="hidden sm:inline">STATUS: </span>
            <strong className="text-white">{missionStatus}</strong>
          </span>
        </div>
      </div>

      {/* Primary Actions & Clean Controls */}
      <div className="flex items-center space-x-1.5 sm:space-x-2.5 shrink-0">
        {/* Benchmark Evaluation Suite Button */}
        <button
          onClick={onOpenBenchmarks}
          className="flex items-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-cyan-400/30 text-[11px] sm:text-xs font-mono text-cyan-400 hover:text-white transition shadow-sm active:scale-95"
        >
          <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
          <span className="hidden md:inline">EVAL SUITE (20/20)</span>
          <span className="hidden sm:inline md:hidden">EVAL (20/20)</span>
          <span className="sm:hidden">EVAL</span>
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="p-1.5 sm:p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 hover:text-white transition active:scale-95 shrink-0"
          title="System Settings & Config"
          aria-label="System Settings"
        >
          <Sliders className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};

export default Header;
