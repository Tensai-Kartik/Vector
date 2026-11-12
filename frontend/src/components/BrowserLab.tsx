import React, { memo, useState, useRef, useEffect } from 'react';
import { Monitor, Lock, ExternalLink, Maximize2, Minimize2, Film, OctagonAlert, FolderOpen, Music, Globe, CheckCircle2, Layers, Eye } from 'lucide-react';
import { api, TabPreviewData } from '../services/api';
import { MissionStepState } from '../types';

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
  authorizedFolderName?: string | null;
  authorizedFolderPerm?: 'granted' | 'prompt' | 'denied' | null;
  onAuthorizeMediaFolder?: () => void;
  onUnlockSavedFolder?: () => void;
  onClearAuthorizedFolder?: () => void;
  onPickLocalMediaFolder?: () => void;
  onSelectLocalFiles?: (files: FileList) => void;
  localMediaError?: string | null;
  openedInChromeUrl?: string | null;
  tabPreview?: TabPreviewData | null;
  steps?: MissionStepState[];
}

const getYoutubeEmbedUrl = (url?: string | null): string | null => {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if (!host.includes('youtube.com') && !host.includes('youtu.be')) return null;
    let vid: string | null = null;
    if (host.includes('youtu.be')) {
      vid = parsed.pathname.replace(/^\/+/, '').split('/')[0] || null;
    } else if (parsed.pathname.startsWith('/watch')) {
      vid = parsed.searchParams.get('v');
    } else if (parsed.pathname.startsWith('/shorts/') || parsed.pathname.startsWith('/embed/') || parsed.pathname.startsWith('/live/')) {
      vid = parsed.pathname.split('/')[2] || null;
    }
    if (vid && /^[a-zA-Z0-9_-]{11}$/.test(vid)) {
      return `https://www.youtube.com/embed/${vid}?autoplay=1&mute=1&playsinline=1&rel=0`;
    }
  } catch {
    // Ignore malformed URLs
  }
  return null;
};

const getHostLabel = (url?: string | null): string => {
  if (!url) return '';
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
};

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
  authorizedFolderName = null,
  authorizedFolderPerm = null,
  onAuthorizeMediaFolder,
  onUnlockSavedFolder,
  onClearAuthorizedFolder,
  onPickLocalMediaFolder,
  onSelectLocalFiles,
  localMediaError = null,
  openedInChromeUrl = null,
  tabPreview = null,
  steps = [],
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [launchingApp, setLaunchingApp] = useState(false);
  const [appFeedback, setAppFeedback] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<'auto' | 'embed' | 'activity'>('auto');
  const [bannerImgFailed, setBannerImgFailed] = useState(false);

  useEffect(() => {
    setPreviewMode('auto');
    setBannerImgFailed(false);
  }, [openedInChromeUrl, tabPreview?.embed_url]);

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
      className={`bg-[#0b0f17] border border-white/10 overflow-hidden shadow-2xl flex flex-col transition-all duration-300 ${isFullscreen
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
                  <span className="hidden min-[400px]:inline">{launchingApp ? 'OPENING...' : (appFeedback || 'APP')}</span>
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
                  <span className="hidden min-[400px]:inline">OPEN</span>
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
              className="hidden sm:flex items-center space-x-1 px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-lg bg-rose-950/70 hover:bg-rose-600 border border-rose-500/40 text-rose-300 hover:text-white transition shadow-sm active:scale-95 shrink-0"
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
                  {authorizedFolderName ? `${authorizedFolderName} (${localMediaFiles.length}):` : `LOCAL MEDIA (${localMediaFiles.length}):`}
                </span>
                {localMediaFiles.slice(0, 12).map((item, idx) => (
                  <button
                    key={item.url}
                    type="button"
                    onClick={() => onSelectLocalMediaIndex?.(idx)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-mono truncate max-w-[180px] shrink-0 transition cursor-pointer ${idx === activeLocalMediaIndex
                        ? 'bg-[#d4ff00] text-black font-bold'
                        : 'bg-[#101622] text-slate-300 hover:text-white border border-white/10'
                      }`}
                    title={item.name}
                  >
                    {item.name}
                  </button>
                ))}
                {onAuthorizeMediaFolder && (
                  <button
                    type="button"
                    onClick={onAuthorizeMediaFolder}
                    className="ml-auto px-2 py-1 rounded-lg bg-[#101622] hover:bg-[#1a2333] border border-white/10 text-cyan-300 font-mono text-[10px] shrink-0 transition cursor-pointer"
                    title="Change authorized media folder"
                  >
                    CHANGE FOLDER
                  </button>
                )}
              </div>
            )}
          </div>
        ) : needsLocalFolderPicker ? (
          <div className="flex flex-col items-center justify-center p-6 sm:p-8 text-center space-y-3 max-w-lg">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center shadow-lg">
              <FolderOpen className="w-5 h-5 text-cyan-300" />
            </div>
            <div>
              <h3 className="text-xs font-mono font-semibold text-cyan-200 uppercase tracking-wider">
                Authorize Local Media Folder (One-Time)
              </h3>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed font-sans">
                Grant read-only permission once to <span className="text-slate-200 font-medium">Videos</span>, <span className="text-slate-200 font-medium">Music</span>, or a subfolder (e.g. <span className="text-slate-200 font-mono text-[10px]">Downloads/Media</span>) and pick <span className="text-cyan-300 font-medium">Allow on every visit</span>. VECTOR will auto-scan and play media with zero file pickers on future runs.
              </p>
              <p className="text-[10px] text-slate-500 mt-1 font-mono">
                Note: Chrome blocks folder-level access on top-level &quot;Downloads&quot; itself.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
              {authorizedFolderName && authorizedFolderPerm !== 'granted' && onUnlockSavedFolder && (
                <button
                  type="button"
                  onClick={onUnlockSavedFolder}
                  className="px-4 py-2 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg transition cursor-pointer"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>UNLOCK &apos;{authorizedFolderName}&apos; &amp; PLAY</span>
                </button>
              )}
              {onAuthorizeMediaFolder && (
                <button
                  type="button"
                  onClick={onAuthorizeMediaFolder}
                  className="px-4 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-2 shadow-lg transition cursor-pointer"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>{authorizedFolderName ? 'CHANGE MEDIA FOLDER' : 'AUTHORIZE MEDIA FOLDER (ONCE)'}</span>
                </button>
              )}
              {onPickLocalMediaFolder && (
                <button
                  type="button"
                  onClick={onPickLocalMediaFolder}
                  className="px-3 py-2 rounded-xl bg-[#101622] hover:bg-[#1a2333] border border-white/15 text-slate-200 font-mono text-[11px] font-semibold transition cursor-pointer"
                  title="Pick specific files directly inside top-level Downloads"
                >
                  PICK FILES IN DOWNLOADS
                </button>
              )}
              {onSelectLocalFiles && (
                <label className="px-3 py-2 rounded-xl bg-[#101622] hover:bg-[#1a2333] border border-white/15 text-slate-300 font-mono text-[11px] font-semibold cursor-pointer transition">
                  <span>BROWSE</span>
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
        ) : openedInChromeUrl ? (() => {
          const derivedYtEmbed = getYoutubeEmbedUrl(openedInChromeUrl);
          const resolvedEmbedUrl =
            tabPreview?.embed_url ||
            derivedYtEmbed ||
            (tabPreview?.embeddable ? (tabPreview?.final_url || openedInChromeUrl) : null);
          const showIframe =
            previewMode === 'embed'
              ? Boolean(resolvedEmbedUrl || openedInChromeUrl)
              : previewMode === 'auto' && Boolean(resolvedEmbedUrl);
          const iframeSrc = resolvedEmbedUrl || openedInChromeUrl;
          const previewTitle = tabPreview?.title || getHostLabel(openedInChromeUrl) || 'Chrome Tab Session';
          const previewDomain = tabPreview?.domain || getHostLabel(openedInChromeUrl);
          const completedCount = steps.filter((s) => s.status === 'completed').length;
          const latestStep = [...steps].reverse().find((s) => s.status === 'running') || steps[steps.length - 1];

          if (showIframe) {
            return (
              <div className="w-full h-full flex flex-col bg-[#05070a]">
                {/* Compact Live Tab Preview Sub-Bar */}
                <div className="bg-[#090e17] border-b border-white/10 px-2.5 sm:px-3 py-1.5 flex items-center justify-between gap-2 shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shrink-0" />
                    <span className="text-[9px] sm:text-[10px] font-mono font-bold text-cyan-300 uppercase tracking-wider shrink-0">
                      LIVE TAB PREVIEW
                    </span>
                    <span className="text-[10px] font-mono text-slate-300 truncate hidden min-[420px]:inline">
                      {previewTitle}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => setPreviewMode('activity')}
                      className="px-2 py-0.5 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-[9px] sm:text-[10px] font-mono text-slate-300 hover:text-white flex items-center gap-1 transition cursor-pointer"
                      title="Inspect page metadata & app actions"
                    >
                      <Layers className="w-2.5 h-2.5 text-[#d4ff00]" />
                      <span>ACTIVITY</span>
                    </button>
                    <a
                      href={openedInChromeUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-0.5 rounded-md bg-[#d4ff00] hover:bg-[#c2ea00] text-black text-[9px] sm:text-[10px] font-mono font-bold flex items-center gap-1 transition"
                      title="Focus real Chrome tab"
                    >
                      <span>OPEN TAB</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  </div>
                </div>

                {/* Live Embedded Page / Video Preview */}
                <div className="flex-1 min-h-0 relative bg-black">
                  <iframe
                    key={iframeSrc}
                    src={iframeSrc}
                    title={previewTitle}
                    className="w-full h-full border-0 bg-[#05070a]"
                    allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                </div>

                {/* Bottom App Activity Strip */}
                {(steps.length > 0 || activeAction) && (
                  <div className="bg-[#080c13] border-t border-white/10 px-2.5 sm:px-3 py-1.5 flex items-center justify-between gap-2 text-[10px] font-mono shrink-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                      <span className="text-slate-200 truncate">
                        {activeAction || latestStep?.intent || `Running in Chrome tab (${previewDomain})`}
                      </span>
                    </div>
                    {steps.length > 0 && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0">
                        {completedCount}/{steps.length} VERIFIED
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          }

          return (
            <div className="w-full h-full overflow-y-auto p-3 sm:p-5 flex flex-col justify-between gap-3 bg-[#06090f]">
              {/* Simulated Chrome Tab Preview Card */}
              <div className="bg-[#0c121e] border border-white/10 rounded-xl overflow-hidden shadow-xl shrink-0">
                {/* Mini Tab Chrome Bar */}
                <div className="bg-[#080c13] border-b border-white/10 px-3 py-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {tabPreview?.favicon_url ? (
                      <img
                        src={tabPreview.favicon_url}
                        alt=""
                        className="w-4 h-4 rounded-sm shrink-0 object-contain"
                      />
                    ) : (
                      <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    )}
                    <span className="text-[11px] font-mono font-semibold text-slate-100 truncate">
                      {previewTitle}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                      {tabPreview?.status_code && tabPreview.status_code < 400
                        ? `LIVE · ${tabPreview.status_code}`
                        : 'CHROME TAB ACTIVE'}
                    </span>
                  </div>
                </div>

                {/* Page Visual Snapshot & Summary */}
                <div className="p-3 sm:p-4 flex flex-col sm:flex-row gap-3 items-start">
                  {tabPreview?.image_url && !bannerImgFailed ? (
                    <img
                      src={tabPreview.image_url}
                      alt={previewTitle}
                      onError={() => setBannerImgFailed(true)}
                      className="w-full sm:w-44 h-28 sm:h-24 object-cover rounded-lg border border-white/10 shrink-0 bg-black"
                    />
                  ) : (
                    <div className="w-full sm:w-32 h-20 sm:h-24 rounded-lg bg-gradient-to-br from-cyan-500/15 via-[#101829] to-[#d4ff00]/10 border border-white/10 flex flex-col items-center justify-center gap-1.5 shrink-0 px-2">
                      {tabPreview?.favicon_url ? (
                        <img
                          src={tabPreview.favicon_url}
                          alt=""
                          className="w-7 h-7 rounded object-contain"
                        />
                      ) : (
                        <Globe className="w-6 h-6 text-cyan-300" />
                      )}
                      <span className="text-[9px] font-mono text-slate-300 truncate max-w-full">
                        {tabPreview?.site_name || previewDomain}
                      </span>
                    </div>
                  )}

                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="text-[10px] font-mono text-cyan-400 truncate">
                      {openedInChromeUrl}
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3 font-sans">
                      {tabPreview?.description ||
                        'Opened directly in your real Chrome session with your signed-in profile, cookies, and zero datacenter bot blocks.'}
                    </p>
                    {tabPreview?.embed_blocked_reason && (
                      <div className="text-[9px] font-mono text-amber-300/90 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-0.5 inline-block">
                        {tabPreview.embed_blocked_reason}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Live App Activity Timeline ("What VECTOR Is Doing") */}
              <div className="bg-[#0b0f17] border border-white/10 rounded-xl p-3 space-y-2 shrink-0">
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
                    <Layers className="w-3 h-3 text-[#d4ff00]" />
                    <span>APP ACTIVITY PREVIEW</span>
                  </span>
                  {steps.length > 0 && (
                    <span className="text-emerald-400 font-bold">
                      {completedCount}/{steps.length} COMPLETED
                    </span>
                  )}
                </div>

                {steps.length > 0 ? (
                  <div className="space-y-1.5">
                    {steps.slice(0, 4).map((step, idx) => (
                      <div
                        key={step.step_id || idx}
                        className="flex items-center justify-between gap-2 text-[10px] font-mono bg-[#080c13] border border-white/5 rounded-lg px-2.5 py-1.5"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                              step.status === 'completed'
                                ? 'bg-emerald-400'
                                : step.status === 'running'
                                ? 'bg-[#d4ff00] animate-ping'
                                : 'bg-cyan-400'
                            }`}
                          />
                          <span className="text-slate-200 truncate">{step.intent}</span>
                        </div>
                        <span
                          className={`text-[9px] uppercase font-bold shrink-0 ${
                            step.status === 'completed'
                              ? 'text-emerald-400'
                              : step.status === 'running'
                              ? 'text-[#d4ff00]'
                              : 'text-slate-400'
                          }`}
                        >
                          {step.status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-[11px] font-mono text-slate-300 bg-[#080c13] border border-white/5 rounded-lg px-2.5 py-2">
                    {activeAction || `Target launched in Chrome tab (${previewDomain}).`}
                  </div>
                )}
              </div>

              {/* Quick Actions */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5 shrink-0">
                <button
                  type="button"
                  onClick={() => setPreviewMode('embed')}
                  className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 font-mono text-[10px] font-semibold flex items-center gap-1.5 transition cursor-pointer"
                  title="Attempt live inline frame inside viewport"
                >
                  <Eye className="w-3 h-3 text-cyan-400" />
                  <span>{resolvedEmbedUrl ? 'VIEW LIVE EMBED' : 'TRY LIVE FRAME'}</span>
                </button>

                <a
                  href={openedInChromeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3.5 py-1.5 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-[11px] font-bold flex items-center gap-1.5 shadow-lg transition"
                >
                  <span>OPEN / FOCUS TARGET TAB</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          );
        })() : (
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
            {onAuthorizeMediaFolder && (
              <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
                {authorizedFolderName ? (
                  <div className="flex flex-wrap items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[#0d1420] border border-white/10 text-[10px] font-mono">
                    <FolderOpen className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="text-slate-200 font-semibold truncate max-w-[140px]">
                      {authorizedFolderName}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${authorizedFolderPerm === 'granted'
                          ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        }`}
                    >
                      {authorizedFolderPerm === 'granted' ? 'AUTO-PLAY READY' : 'NEEDS UNLOCK'}
                    </span>
                    <button
                      type="button"
                      onClick={onAuthorizeMediaFolder}
                      className="text-cyan-400 hover:text-cyan-300 underline ml-1 cursor-pointer"
                    >
                      Change
                    </button>
                    {onClearAuthorizedFolder && (
                      <button
                        type="button"
                        onClick={onClearAuthorizedFolder}
                        className="text-slate-500 hover:text-rose-400 ml-1 cursor-pointer"
                        title="Forget saved media folder permission"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={onAuthorizeMediaFolder}
                    className="px-3 py-1.5 rounded-xl bg-[#0d1420] hover:bg-[#131d2e] border border-white/10 text-cyan-300 font-mono text-[10px] font-semibold flex items-center space-x-1.5 transition cursor-pointer"
                    title="Grant one-time folder permission for zero-click local media auto-play"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    <span>Authorize Local Media Folder</span>
                  </button>
                )}
              </div>
            )}
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
