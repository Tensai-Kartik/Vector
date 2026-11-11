import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  OctagonAlert,
  Menu,
  X,
  Activity,
  Cpu,
  Terminal,
} from 'lucide-react';

interface HeaderProps {
  demoMode: boolean;
  setDemoMode: (val: boolean) => void;
  onOpenBenchmarks: () => void;
  missionStatus?: string;
  onKillMission?: () => void;
  activeMissionId?: string | null;
  backendStatus?: 'checking' | 'waking' | 'online' | 'offline';
}

export const Header: React.FC<HeaderProps> = ({
  demoMode,
  setDemoMode,
  onOpenBenchmarks,
  missionStatus = 'ready',
  onKillMission,
  backendStatus = 'checking',
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isMissionActive =
    missionStatus === 'running' ||
    missionStatus === 'planning' ||
    missionStatus === 'inspecting' ||
    missionStatus === 'awaiting_approval' ||
    missionStatus === 'queued';

  const statusDotColor =
    missionStatus === 'running'
      ? 'bg-[#d4ff00] animate-ping'
      : missionStatus === 'awaiting_approval'
        ? 'bg-amber-400 animate-pulse'
        : missionStatus === 'completed'
          ? 'bg-emerald-400'
          : missionStatus === 'failed'
            ? 'bg-rose-400'
            : 'bg-cyan-400';

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileMenuOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);

    const mq = window.matchMedia('(min-width: 640px)');
    const onMediaChange = (e: MediaQueryListEvent) => {
      if (e.matches) setMobileMenuOpen(false);
    };
    mq.addEventListener('change', onMediaChange);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      mq.removeEventListener('change', onMediaChange);
    };
  }, []);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  return (
              <>
                <header className="border-b border-white/10 bg-[#07090e]/95 backdrop-blur-xl px-3 sm:px-5 lg:px-6 py-2.5 sm:py-3 flex items-center justify-between gap-2 sticky top-0 z-40 transition-all">
                  {/* Left: Mobile-only Hamburger + Smooth Sliding Brand | Tablet/Desktop Brand + Status */}
                  <div className="flex items-center gap-2 sm:gap-3 lg:gap-4 flex-1 min-w-0 overflow-hidden">
                    {/* Mobile-only Hamburger Button on the far left (beside the logo) */}
                    <button
                      type="button"
                      onClick={() => setMobileMenuOpen((prev) => !prev)}
                      aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
                      aria-expanded={mobileMenuOpen}
                      className="sm:hidden w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-slate-200 hover:text-white transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] active:scale-95 shrink-0"
                    >
                      <span
                        className={`transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] flex items-center justify-center ${mobileMenuOpen ? 'rotate-90 scale-90 text-[#d4ff00]' : 'rotate-0 scale-100'
                          }`}
                      >
                        {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
                      </span>
                    </button>

                    {/* Mobile Brand Button beside Hamburger — smoothly slides left into the opening drawer */}
                    <button
                      type="button"
                      onClick={() => setMobileMenuOpen(true)}
                      aria-label="VECTOR menu"
                      className={`sm:hidden flex items-center space-x-2 overflow-hidden whitespace-nowrap transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] shrink-0 ${mobileMenuOpen
                          ? 'max-w-0 opacity-0 -translate-x-4 pointer-events-none'
                          : 'max-w-[180px] opacity-100 translate-x-0'
                        }`}
                    >
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#d4ff00]/20 to-[#d4ff00]/5 border border-[#d4ff00]/40 flex items-center justify-center shadow-lg shadow-[#d4ff00]/15 p-1 shrink-0">
                        <img
                          src="/logo_bg.png"
                          alt="VECTOR Logo"
                          className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(212,255,0,0.35)]"
                        />
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <span className="font-bold text-white tracking-wider text-sm font-mono">VECTOR</span>
                          <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30 tracking-widest">
                            v1.0
                          </span>
                      </div>
                    </button>

                    {/* Desktop & Tablet Brand Logo */}
                    <div className="hidden sm:flex items-center space-x-2.5 lg:space-x-3 shrink-0">
                      <div className="w-8 h-8 lg:w-9 lg:h-9 rounded-xl bg-gradient-to-tr from-[#d4ff00]/20 to-[#d4ff00]/5 border border-[#d4ff00]/40 flex items-center justify-center shadow-lg shadow-[#d4ff00]/15 p-1 transition hover:border-[#d4ff00]/70 shrink-0">
                        <img
                          src="/logo_bg.png"
                          alt="VECTOR Logo"
                          className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(212,255,0,0.35)]"
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center space-x-1.5 lg:space-x-2">
                          <span className="font-bold text-white tracking-wider text-sm font-mono">VECTOR</span>
                          <span className="text-[9px] font-mono font-bold px-1.5 lg:px-2 py-0.5 rounded-full bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30 tracking-widest">
                            v1.0
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-mono leading-none mt-0.5 truncate hidden lg:block">
                          Autonomous Web Operator · Hybrid API + Playwright
                        </p>
                      </div>
                    </div>

                  <div className="h-5 w-px bg-white/10 hidden md:block shrink-0" />

                    {/* Tablet/Desktop Dynamic Status Pill */}
                    <div className="hidden sm:flex items-center space-x-1.5 lg:space-x-2 bg-white/5 px-2 lg:px-3 py-1 rounded-full border border-white/10 text-[10px] lg:text-xs font-mono shrink-0">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotColor}`} />
                      <span className="text-slate-300 uppercase tracking-wider text-[9px] lg:text-[10px]">
                        <span className="hidden lg:inline">STATUS: </span>
                        <strong className="text-white">{missionStatus}</strong>
                      </span>
                    </div>

                    {/* Tablet/Desktop Backend Connectivity Status Pill */}
                    {backendStatus === 'online' ? (
                      <div
                        className="hidden sm:flex items-center space-x-1.5 px-2 lg:px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[9px] lg:text-[10px] font-mono text-emerald-400 shrink-0"
                        title="Vector FastAPI Backend connected and operational"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                        <span className="hidden lg:inline">BACKEND ONLINE</span>
                        <span className="lg:hidden">ONLINE</span>
                      </div>
                    ) : backendStatus === 'waking' ? (
                      <div
                        className="hidden sm:flex items-center space-x-1.5 px-2 lg:px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-[9px] lg:text-[10px] font-mono text-amber-300 shrink-0 animate-pulse"
                        title="Render free tier spins down after 15m of idle time. Currently waking up cloud instance (~25-40s)..."
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping shrink-0" />
                        <span className="hidden lg:inline">WAKING BACKEND...</span>
                        <span className="lg:hidden">WAKING...</span>
                      </div>
                    ) : backendStatus === 'offline' ? (
                      <div
                        className="hidden sm:flex items-center space-x-1.5 px-2 lg:px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/40 text-[9px] lg:text-[10px] font-mono text-rose-300 shrink-0 animate-pulse"
                        title="Backend offline! Run: python -m uvicorn backend.app.main:app --reload"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
                        <span className="hidden lg:inline">BACKEND OFFLINE</span>
                        <span className="lg:hidden">OFFLINE</span>
                      </div>
                    ) : null}
                  </div>

                      {/* Right: Mobile compact status (+ Stop only when running) | Tablet & Desktop Controls */}
                      <div className="flex items-center space-x-1.5 sm:space-x-2 lg:space-x-2.5 shrink-0">
                        {/* Mobile-only clean compact status pill (never collides with buttons) */}
                        <div className="sm:hidden flex items-center space-x-1.5 bg-white/5 px-2.5 py-1 rounded-full border border-white/10 text-[10px] font-mono shrink-0 max-w-[130px]">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotColor}`} />
                          <span className="text-white font-bold uppercase tracking-wider truncate">
                            {missionStatus}
                          </span>
                        </div>

                            {/* Mobile-only urgent STOP button only while mission is actively executing */ }
          {onKillMission && isMissionActive && (
                          <button
                            type="button"
                            onClick={onKillMission}
                            className="sm:hidden flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-mono text-[10px] font-bold transition shadow-lg shadow-rose-600/30 animate-pulse active:scale-95 shrink-0"
                            title="Abort active mission"
                          >
                            <OctagonAlert className="w-3.5 h-3.5 shrink-0" />
                            <span>KILL</span>
                          </button>
          )}

                        {/* Tablet & Desktop Kill / Abort Mission Button */}
                        {onKillMission && (
                          isMissionActive ? (
                            <button
                              type="button"
                              onClick={onKillMission}
                              className="hidden sm:flex items-center space-x-1.5 px-2.5 lg:px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-mono text-[11px] lg:text-xs font-bold transition shadow-lg shadow-rose-600/30 animate-pulse active:scale-95 shrink-0 whitespace-nowrap"
                              title="Immediately abort active mission and close browser"
                            >
                              <OctagonAlert className="w-3.5 h-3.5 shrink-0" />
                              <span className="hidden lg:inline">KILL MISSION</span>
                              <span className="lg:hidden">KILL</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={onKillMission}
                              className="hidden sm:flex items-center space-x-1.5 px-2.5 lg:px-3 py-1.5 rounded-xl bg-rose-950/60 hover:bg-rose-900 border border-rose-500/30 text-rose-300 hover:text-white font-mono text-[10px] lg:text-[11px] font-semibold transition active:scale-95 shrink-0 whitespace-nowrap"
                              title="Force close any browser session and kill background audio/process"
                            >
                              <OctagonAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                              <span className="hidden lg:inline">KILL BROWSER</span>
                              <span className="lg:hidden">KILL</span>
                            </button>
                          )
                        )}

                        {/* Tablet & Desktop Benchmark Evaluation Suite Button */}
                        <button
                          type="button"
                          onClick={onOpenBenchmarks}
                          className="hidden sm:flex items-center space-x-1.5 px-2.5 lg:px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-cyan-400/30 text-[11px] lg:text-xs font-mono text-cyan-400 hover:text-white transition shadow-sm active:scale-95 shrink-0 whitespace-nowrap"
                        >
                          <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                          <span className="hidden lg:inline">EVAL SUITE (21/21)</span>
                          <span className="lg:hidden">EVAL (21/21)</span>
                        </button>
                      </div>
                    </header>

      {/* Mobile-only Gemini-Style Left Slide-Out Hamburger Drawer (stays mounted for smooth open/close transitions) */}
                  <div
                    aria-hidden={!mobileMenuOpen}
                    className={`sm:hidden fixed inset-0 z-50 transition-all duration-300 ${mobileMenuOpen ? 'pointer-events-auto' : 'pointer-events-none'
                      }`}
                  >
                    {/* Dimmed Backdrop Scrim */}
                    <div
                      onClick={() => setMobileMenuOpen(false)}
                      className={`fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity duration-300 ease-out ${mobileMenuOpen ? 'opacity-100' : 'opacity-0'
                        }`}
                    />

                    {/* Slide-Out Drawer Panel */}
                    <aside
                      className={`fixed top-0 left-0 bottom-0 w-[290px] max-w-[85vw] bg-[#080b12]/98 backdrop-blur-2xl border-r border-white/10 shadow-2xl flex flex-col transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
                        }`}
                    >
                      {/* Drawer Top Brand Header — Logo moves smoothly to top of drawer like Gemini Mobile App */}
                      <div className="px-4 py-3.5 border-b border-white/10 flex items-center justify-between gap-2 bg-[#0b0f17]/80 shrink-0">
                        <div
                          className={`flex items-center space-x-2.5 min-w-0 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] ${mobileMenuOpen ? 'opacity-100 translate-x-0 delay-75' : 'opacity-0 translate-x-4'
                            }`}
                        >
                          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#d4ff00]/20 to-[#d4ff00]/5 border border-[#d4ff00]/40 flex items-center justify-center shadow-lg shadow-[#d4ff00]/15 p-1 shrink-0">
                            <img
                              src="/logo_bg.png"
                              alt="VECTOR Logo"
                              className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(212,255,0,0.35)]"
                            />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center space-x-1.5">
                              <span className="font-bold text-white tracking-wider text-sm font-mono">VECTOR</span>
                              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30 tracking-widest">
                                v1.0
                              </span>
                            </div>
                            <p className="text-[9px] text-slate-400 font-mono leading-tight truncate mt-0.5">
                              Autonomous Web Operator
                            </p>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => setMobileMenuOpen(false)}
                          aria-label="Close menu"
                          className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-slate-300 hover:text-white transition active:scale-95 shrink-0"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Drawer Content */}
                      <div className="flex-1 overflow-y-auto p-4 space-y-5 font-mono">
                        {/* Live Telemetry Status Cards */}
                        <div className="space-y-2">
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider px-1">
                            SYSTEM STATUS
                          </div>

                          <div className="bg-[#0d121c] border border-white/10 rounded-xl p-3 space-y-2.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-400 flex items-center gap-2">
                                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                                <span>Mission State</span>
                              </span>
                              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-white uppercase">
                                <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
                                {missionStatus}
                              </span>
                            </div>

                            <div className="flex items-center justify-between text-xs pt-2 border-t border-white/5">
                              <span className="text-slate-400 flex items-center gap-2">
                                <Terminal className="w-3.5 h-3.5 text-[#d4ff00]" />
                                <span>Backend API</span>
                              </span>
                              {backendStatus === 'online' ? (
                                <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-bold">
                                  ONLINE
                                </span>
                              ) : backendStatus === 'waking' ? (
                                <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-[10px] text-amber-300 font-bold animate-pulse">
                                  WAKING...
                                </span>
                              ) : backendStatus === 'offline' ? (
                                <span className="px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-[10px] text-rose-300 font-bold">
                                  OFFLINE
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full bg-white/5 text-[10px] text-slate-400">
                                  CHECKING
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Primary Navigation & Controls */}
                        <div className="space-y-2">
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider px-1">
                            OPERATOR CONTROLS
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setMobileMenuOpen(false);
                              onOpenBenchmarks();
                            }}
                            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-cyan-400/30 text-xs text-cyan-300 hover:text-white transition active:scale-[0.98]"
                          >
                            <span className="flex items-center space-x-2.5">
                              <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0" />
                              <span className="font-semibold">EVAL SUITE</span>
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-400/15 text-cyan-300 font-bold">
                              21/21
                            </span>
                          </button>

                          {onKillMission && (
                            <button
                              type="button"
                              onClick={() => {
                                onKillMission();
                                setMobileMenuOpen(false);
                              }}
                              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition active:scale-[0.98] ${isMissionActive
                                  ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30'
                                  : 'bg-rose-950/60 hover:bg-rose-900 border border-rose-500/30 text-rose-300 hover:text-white'
                                }`}
                            >
                              <span className="flex items-center space-x-2.5">
                                <OctagonAlert className="w-4 h-4 shrink-0" />
                                <span>{isMissionActive ? 'KILL ACTIVE MISSION' : 'KILL BROWSER SESSION'}</span>
                              </span>
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => setDemoMode(!demoMode)}
                            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-[#0d121c] hover:bg-[#121927] border border-white/10 text-xs text-slate-200 transition active:scale-[0.98]"
                          >
                            <span className="flex items-center space-x-2.5">
                              <Cpu className="w-4 h-4 text-[#d4ff00] shrink-0" />
                              <span>Synthetic Demo Mode</span>
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${demoMode
                                  ? 'bg-[#d4ff00]/20 text-[#d4ff00] border border-[#d4ff00]/40'
                                  : 'bg-white/5 text-slate-400 border border-white/10'
                                }`}
                            >
                              {demoMode ? 'ON' : 'OFF'}
                            </span>
                          </button>
                        </div>
                      </div>

                      {/* Drawer Footer */}
                      <div className="p-4 border-t border-white/10 text-[10px] font-mono text-slate-500 bg-[#06080d] shrink-0">
                        <div className="flex items-center justify-between">
                          <span>HYBRID ROUTER</span>
                          <span className="text-slate-400">API + PLAYWRIGHT</span>
                        </div>
                      </div>
                    </aside>
                  </div>
              </>
              );
};

              export default Header;
