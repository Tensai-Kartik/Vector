import React, { memo, useState, useRef, useEffect } from 'react';
import { Monitor, Lock, ExternalLink, Maximize2, Minimize2, Film, OctagonAlert, FolderOpen, Music } from 'lucide-react';
import { api } from '../services/api';

export interface LocalMediaFileEntry {
  name: string;
  url: string;
  kind: 'video' | 'audio';
  size: number;
}

interface BrowserLabProps {
  currentUrl?: string;
  pageTitle?: string;
  screencastFrame?: string | null;
  activeAction?: string;
  isConnected: boolean;
  isStreaming: boolean;
  onKill?: () => void;
  localMediaFiles?: LocalMediaFileEntry[];
  activeLocalMediaIndex?: number;
  onSelectLocalMediaIndex?: (idx: number) => void;
  needsLocalFolderPicker?: boolean;
  onPickLocalMediaFolder?: () => void;
  onPickLocalSubfolder?: () => void;
  onSelectLocalFiles?: (files: FileList) => void;
  localMediaError?: string | null;
  openedInChromeUrl?: string | null;
}

export const BrowserLab: React.FC<BrowserLabProps> = memo(({
  currentUrl = 'about:blank',
  screencastFrame,
  activeAction,
  isStreaming,
  onKill,
  localMediaFiles = [],
  activeLocalMediaIndex = 0,
  onSelectLocalMediaIndex,
  needsLocalFolderPicker = false,
  onPickLocalMediaFolder,
  onPickLocalSubfolder,
  onSelectLocalFiles,
  localMediaError = null,
  openedInChromeUrl = null,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [launchingApp, setLaunchingApp] = useState(false);
  const [appFeedback, setAppFeedback] = useState<string | null>(null);

  const activeLocalMedia = localMediaFiles[activeLocalMediaIndex] || null;
  const isLiveUrl = Boolean(currentUrl && currentUrl !== 'about:blank');
  const isBrowserLocalMedia = Boolean(currentUrl && currentUrl.startsWith('local://'));
  const isLocalMedia = Boolean(
    currentUrl && !isBrowserLocalMedia && (
      currentUrl.startsWith('file:') ||
      /\.(mkv|mp4|webm|avi|mov|m4a|mp3|wav|flac)(\?.*)?$/i.test(currentUrl)
    )
  );


  const handleOpenDefaultApp = async () => {
    if (!currentUrl) return;
    setLaunchingApp(true);
    try {
      await api.launchFile(currentUrl);
      setAppFeedback('Opened in Player!');
      setTimeout(() => setAppFeedback(null), 3000);
    } catch (e) {
      setAppFeedback('Open failed');
      setTimeout(() => setAppFeedback(null), 3000);
    } finally {
      setLaunchingApp(false);
    }
  };

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        if (containerRef.current?.requestFullscreen) {
          await containerRef.current.requestFullscreen();
          setIsFullscreen(true);
        } else {
          setIsFullscreen((prev) => !prev);
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
          setIsFullscreen(false);
        }
      }
    } catch (e) {
      setIsFullscreen((prev) => !prev);
    }
  };

  useEffect(() => {
    const handler = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  return (
    <div
      ref={containerRef}
      className={`bg-[#0b0f17] border border-white/10 overflow-hidden shadow-2xl flex flex-col transition-all duration-300 ${
        isFullscreen
          ? 'fixed inset-0 z-50 h-screen w-screen rounded-none'
          : 'rounded-2xl h-[380px] sm:h-[460px] lg:h-[520px]'
      }`}
    >
      {/* Sleek Chrome Bar */}
      <div className="bg-[#080c13] border-b border-white/5 px-2.5 sm:px-4 py-2 sm:py-3 flex items-center justify-between shrink-0 gap-2 sm:gap-3">
        {/* Brand Icon & Viewport Label */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
          <div className="w-5 h-5 rounded-md bg-[#d4ff00]/10 border border-[#d4ff00]/30 flex items-center justify-center">
            <Monitor className="w-3 h-3 text-[#d4ff00]" />
          </div>
          <span className="text-xs font-mono font-semibold tracking-wider text-slate-200 hidden md:inline">
            BROWSER VIEWPORT
          </span>
        </div>

        {/* Minimal Glass Address Bar */}
        <div className="flex-1 min-w-0 mx-1 sm:mx-2">
          <div className="bg-[#101622] border border-white/10 hover:border-white/20 rounded-xl px-2.5 sm:px-3 py-1 sm:py-1.5 flex items-center justify-between text-xs font-mono transition-all">
            <div className="flex items-center space-x-1.5 sm:space-x-2 overflow-hidden mr-1 sm:mr-2 min-w-0">
              <Lock className={`w-3 h-3 shrink-0 ${isLiveUrl ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span className="truncate text-slate-200 text-[10px] sm:text-[11px] select-all">
                {currentUrl}
              </span>
            </div>

            <div className="flex items-center space-x-1 sm:space-x-1.5 shrink-0">
              {isLocalMedia && (
                <button
                  type="button"
                  onClick={handleOpenDefaultApp}
                  disabled={launchingApp}
                  className="flex items-center space-x-1 px-2 py-0.5 sm:py-1 rounded-lg bg-[#d4ff00]/15 hover:bg-[#d4ff00] hover:text-black text-[#d4ff00] text-[9px] sm:text-[10px] font-semibold transition shrink-0 border border-[#d4ff00]/30 shadow-sm"
                  title="Open video in default media player"
                >
                  <Film className="w-2.5 h-2.5" />
                  <span className="hidden xs:inline">{launchingApp ? 'OPENING...' : (appFeedback || 'APP')}</span>
                </button>
              )}

              {!isBrowserLocalMedia && (
                <a
                  href={isLiveUrl ? currentUrl : 'https://www.youtube.com'}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    if (currentUrl && currentUrl.startsWith('file://')) {
                      e.preventDefault();
                      handleOpenDefaultApp();
                    }
                  }}
                  className="flex items-center space-x-1 px-2 py-0.5 sm:py-1 rounded-lg bg-[#1a2333] hover:bg-[#d4ff00] hover:text-black text-slate-300 text-[9px] sm:text-[10px] font-semibold transition shrink-0 shadow-sm cursor-pointer"
                  title="Open current webpage in a new browser tab"
                >
                  <span className="hidden xs:inline">OPEN</span>
                  <ExternalLink className="w-2.5 h-2.5" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right Status & Fullscreen Actions */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 text-[10px] sm:text-[11px] font-mono shrink-0">
          {onKill && (
            <button
              type="button"
              onClick={onKill}
              className="flex items-center space-x-1 px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-lg bg-rose-950/70 hover:bg-rose-600 border border-rose-500/40 text-rose-300 hover:text-white transition shadow-sm active:scale-95 shrink-0"
              title="Force terminate browser session and kill background audio/process"
            >
              <OctagonAlert className="w-3 h-3 text-rose-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline">KILL</span>
            </button>
          )}

          <div className="flex items-center space-x-1 sm:space-x-1.5 bg-[#101622] px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-lg border border-white/5">
            <span className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <span className={isStreaming ? 'text-emerald-400 font-semibold text-[9px] sm:text-[10px]' : 'text-slate-400 text-[9px] sm:text-[10px]'}>
              {isStreaming ? 'LIVE' : 'STANDBY'}
            </span>
          </div>

          <button
            type="button"
            onClick={toggleFullscreen}
            className="flex items-center space-x-1 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-[#101622] hover:bg-[#1a2333] text-slate-200 hover:text-[#d4ff00] border border-white/10 transition shadow-sm"
            title={isFullscreen ? 'Exit Fullscreen (ESC)' : 'Expand to Fullscreen View'}
          >
            {isFullscreen ? (
              <Minimize2 className="w-3 sm:w-3.5 h-3 sm:h-3.5 text-[#d4ff00]" />
            ) : (
              <Maximize2 className="w-3 sm:w-3.5 h-3 sm:h-3.5" />
            )}
            <span className="text-[10px] font-semibold uppercase tracking-wider hidden md:inline">
              {isFullscreen ? 'Exit' : 'Fullscreen'}
            </span>
          </button>
        </div>
      </div>

      {/* Viewport Display Canvas */}
      <div className="flex-1 bg-[#05070a] relative flex items-center justify-center overflow-hidden select-none">
        {activeLocalMedia ? (
          <div className="w-full h-full flex flex-col bg-black">
            <div className="flex-1 min-h-0 flex items-center justify-center p-2">
              {activeLocalMedia.kind === 'audio' ? (
                <div className="flex flex-col items-center space-y-3 bg-[#0b0f17] border border-white/10 rounded-2xl p-6 max-w-md w-full">
                  <div className="w-12 h-12 rounded-2xl bg-[#d4ff00]/15 border border-[#d4ff00]/30 flex items-center justify-center">
                    <Music className="w-6 h-6 text-[#d4ff00]" />
                  </div>
                  <div className="text-xs font-mono text-slate-200 truncate max-w-full">
                    {activeLocalMedia.name}
                  </div>
                  <audio
                    key={activeLocalMedia.url}
                    controls
                    autoPlay
                    src={activeLocalMedia.url}
                    className="w-full"
                  />
                </div>
              ) : (
                <video
                  key={activeLocalMedia.url}
                  controls
                  autoPlay
                  playsInline
                  src={activeLocalMedia.url}
                  className="w-full h-full object-contain bg-black rounded-lg"
                />
              )}
            </div>
            {localMediaFiles.length > 0 && (
              <div className="bg-[#080c13] border-t border-white/10 px-3 py-2 flex items-center gap-2 overflow-x-auto shrink-0">
                <span className="text-[10px] font-mono text-slate-400 uppercase shrink-0">
                  LOCAL MEDIA ({localMediaFiles.length}):
                </span>
                {localMediaFiles.slice(0, 12).map((item, idx) => (
                  <button
                    key={item.url}
                    type="button"
                    onClick={() => onSelectLocalMediaIndex?.(idx)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-mono truncate max-w-[180px] shrink-0 transition cursor-pointer ${
                      idx === activeLocalMediaIndex
                        ? 'bg-[#d4ff00] text-black font-bold'
                        : 'bg-[#101622] text-slate-300 hover:text-white border border-white/10'
                    }`}
                    title={item.name}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : needsLocalFolderPicker ? (
          <div className="flex flex-col items-center justify-center p-6 sm:p-8 text-center space-y-3 max-w-md">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center shadow-lg">
              <FolderOpen className="w-5 h-5 text-cyan-300" />
            </div>
            <div>
              <h3 className="text-xs font-mono font-semibold text-cyan-200 uppercase tracking-wider">
                Local Downloads Permission Required
              </h3>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed font-sans">
                VECTOR runs Playwright in the cloud container and cannot read your PC&apos;s Downloads folder without permission. Grant read-only folder access to play your latest media directly here.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
              {onPickLocalMediaFolder && (
                <button
                  type="button"
                  onClick={onPickLocalMediaFolder}
                  className="px-4 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg transition cursor-pointer"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>SELECT MEDIA IN DOWNLOADS</span>
                </button>
              )}
              {onSelectLocalFiles && (
                <label className="px-3 py-2 rounded-xl bg-[#101622] hover:bg-[#1a2333] border border-white/15 text-slate-200 font-mono text-[11px] font-semibold cursor-pointer transition">
                  <span>BROWSE FILES</span>
                  <input
                    type="file"
                    multiple
                    accept="video/*,audio/*,.mkv,.mp4,.webm,.avi,.mov,.mp3,.m4a,.wav,.flac"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        onSelectLocalFiles(e.target.files);
                      }
                    }}
                  />
                </label>
              )}
              {onPickLocalSubfolder && (
                <button
                  type="button"
                  onClick={onPickLocalSubfolder}
                  className="px-3 py-2 rounded-xl bg-[#101622] hover:bg-[#1a2333] border border-white/15 text-slate-300 font-mono text-[11px] font-semibold transition cursor-pointer"
                  title="Scan a custom subfolder (Chrome blocks root Downloads folder scans)"
                >
                  SCAN SUBFOLDER
                </button>
              )}
            </div>
            {localMediaError && (
              <p className="text-[11px] font-mono text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-1.5">
                {localMediaError}
              </p>
            )}
          </div>
        ) : screencastFrame ? (
          <div className="w-full h-full relative flex items-center justify-center bg-black">
            <img
              src={`data:image/jpeg;base64,${screencastFrame}`}
              alt="Playwright live viewport"
              decoding="async"
              className="w-full h-full object-contain pointer-events-none"
              style={{ willChange: 'contents', transform: 'translateZ(0)' }}
            />
            {/* Live Indicator Pill */}
            <div className="absolute top-2.5 right-2.5 pointer-events-none">
              <span className="px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-black/80 backdrop-blur-md border border-white/10 text-emerald-400 text-[9px] sm:text-[10px] font-mono font-medium flex items-center gap-1.5 shadow-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                PLAYWRIGHT SESSION
              </span>
            </div>
            {!isStreaming && isLiveUrl && currentUrl.startsWith('http') && (
              <a
                href={currentUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute bottom-3 right-3 px-3 py-1.5 rounded-xl bg-black/85 hover:bg-[#d4ff00] text-slate-200 hover:text-black border border-white/15 font-mono text-[10px] font-bold flex items-center space-x-1.5 shadow-xl transition"
                title="Open this page in your own browser tab"
              >
                <span>OPEN IN YOUR BROWSER</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        ) : openedInChromeUrl ? (
          <div className="flex flex-col items-center justify-center p-6 sm:p-8 text-center space-y-3 max-w-md">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center shadow-lg">
              <ExternalLink className="w-5 h-5 text-cyan-300" />
            </div>
            <div>
              <h3 className="text-xs font-mono font-semibold text-cyan-200 uppercase tracking-wider">
                Opened in Your Chrome Session
              </h3>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed font-sans">
                Target launched directly in a new Chrome tab/window with your signed-in accounts, history, passwords, permissions, and no datacenter bot-filter.
              </p>
            </div>
            <a
              href={openedInChromeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg transition"
            >
              <span>OPEN / FOCUS TARGET TAB</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-6 sm:p-8 text-center space-y-2 sm:space-y-3 max-w-sm">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-tr from-[#121824] to-[#1e293b] border border-white/10 flex items-center justify-center shadow-lg">
              <Monitor className="w-4 h-4 sm:w-5 h-5 text-slate-300" />
            </div>

            <div>
              <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
                Autonomous Browser Ready
              </h3>
              <p className="text-[10px] sm:text-[11px] text-slate-400 mt-1 leading-relaxed font-sans">
                Dispatch any web or API task. Live screencast streams here, and Playwright executes actions autonomously.
              </p>
            </div>
          </div>
        )}

        {/* Minimal Floating Action Pill */}
        {activeAction && (
          <div className="absolute bottom-3 left-3 right-3 sm:bottom-4 sm:left-4 sm:right-4 bg-black/85 backdrop-blur-xl border border-white/15 rounded-xl px-3 sm:px-4 py-2 sm:py-2.5 flex items-center justify-between shadow-2xl animate-in fade-in duration-200">
            <div className="flex items-center space-x-2 sm:space-x-2.5 overflow-hidden mr-2">
              <span className="w-2 h-2 rounded-full bg-[#d4ff00] animate-ping shrink-0" />
              <div className="truncate">
                <span className="text-[8px] sm:text-[9px] font-mono font-bold text-[#d4ff00] block uppercase tracking-wider">
                  ACTIVE ACTION
                </span>
                <span className="text-[11px] sm:text-xs font-mono text-slate-100 truncate block">
                  {activeAction}
                </span>
              </div>
            </div>
            <span className="text-[9px] sm:text-[10px] font-mono px-1.5 sm:px-2 py-0.5 rounded bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30 shrink-0 font-medium">
              EXECUTING
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

BrowserLab.displayName = 'BrowserLab';

export default BrowserLab;
