import React, { useState, useEffect } from 'react';
import { X, Sliders, Shield, Key, Cpu, Globe, Check } from 'lucide-react';
import { api } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [llmProvider, setLlmProvider] = useState<'mock' | 'gemini'>('mock');
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-2.5-flash');
  const [allowedDomains, setAllowedDomains] = useState('localhost,127.0.0.1,api.github.com,github.com');
  const [browserHeadless, setBrowserHeadless] = useState(true);
  const [savedMsg, setSavedMsg] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.getSettings().then((s) => {
        setLlmProvider(s.llm_provider || 'mock');
        setGeminiModel(s.gemini_model || 'gemini-2.5-flash');
        if (s.allowed_domains) {
          setAllowedDomains(s.allowed_domains.join(','));
        }
        setBrowserHeadless(s.browser_headless ?? true);
      }).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.updateSettings({
        llm_provider: llmProvider,
        gemini_api_key: geminiApiKey,
        gemini_model: geminiModel,
        allowed_domains: allowedDomains.split(',').map((d) => d.trim()),
        browser_headless: browserHeadless,
      });
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 2500);
    } catch (err) {
      console.error('Failed to update settings', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div className="bg-[#0b0f17] border border-white/10 rounded-2xl w-full max-w-xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-[#080c13] border-b border-white/5 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center space-x-2 sm:space-x-2.5 min-w-0">
            <div className="w-6 h-6 rounded-lg bg-cyan-400/10 border border-cyan-400/30 flex items-center justify-center p-0.5 shrink-0">
              <img src="/logo_bg.png" alt="VECTOR" className="w-full h-full object-contain" />
            </div>
            <h2 className="text-xs sm:text-sm font-mono font-semibold text-slate-100 uppercase tracking-wider truncate">
              VECTOR System Settings & Config
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition p-1 shrink-0">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-4 sm:p-6 space-y-3.5 sm:space-y-4 font-mono text-xs overflow-y-auto flex-1">
          {/* Provider Selection */}
          <div className="space-y-1.5">
            <label className="text-slate-400 uppercase text-[10px] tracking-wider block">
              Planner Engine Provider
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
              <button
                type="button"
                onClick={() => setLlmProvider('mock')}
                className={`p-3 rounded-xl border text-left transition flex flex-col space-y-1 ${
                  llmProvider === 'mock'
                    ? 'border-[#d4ff00] bg-[#d4ff00]/10 text-white'
                    : 'border-white/5 bg-[#080c13] text-slate-400 hover:border-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <Cpu className="w-3.5 h-3.5 text-[#d4ff00]" />
                  <span className="font-bold text-xs">Deterministic Planner</span>
                </div>
                <span className="text-[10px] text-slate-400">Built-in deterministic logic & 20/20 benchmarks</span>
              </button>

              <button
                type="button"
                onClick={() => setLlmProvider('gemini')}
                className={`p-3 rounded-xl border text-left transition flex flex-col space-y-1 ${
                  llmProvider === 'gemini'
                    ? 'border-cyan-400 bg-cyan-950/40 text-white'
                    : 'border-white/5 bg-[#080c13] text-slate-400 hover:border-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <Key className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="font-bold text-xs">Google Gemini LLM</span>
                </div>
                <span className="text-[10px] text-slate-400">Dynamic planning with Gemini 2.5 Flash</span>
              </button>
            </div>
          </div>

          {/* Gemini API Key */}
          {llmProvider === 'gemini' && (
            <div className="space-y-1">
              <label className="text-slate-400 uppercase text-[10px] tracking-wider block">
                Gemini API Key
              </label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(e) => setGeminiApiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full bg-[#080c13] border border-white/10 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
              />
            </div>
          )}

          {/* Domain Allowlist */}
          <div className="space-y-1">
            <label className="text-slate-400 uppercase text-[10px] tracking-wider block">
              Default Domain Allowlist (Comma Separated)
            </label>
            <input
              type="text"
              value={allowedDomains}
              onChange={(e) => setAllowedDomains(e.target.value)}
              className="w-full bg-[#080c13] border border-white/10 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-[#d4ff00]"
            />
          </div>

          {/* Headless Toggle */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-[#080c13] border border-white/5">
            <div>
              <span className="font-semibold text-slate-200 block text-xs">Default Headless Playwright</span>
              <span className="text-[10px] text-slate-400">Launch background browser unless specified</span>
            </div>
            <input
              type="checkbox"
              checked={browserHeadless}
              onChange={(e) => setBrowserHeadless(e.target.checked)}
              className="rounded bg-black border-white/20 text-[#d4ff00] focus:ring-[#d4ff00] h-4 w-4"
            />
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-white/5 flex items-center justify-between">
            {savedMsg && (
              <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                <Check className="w-3.5 h-3.5" /> Settings saved successfully
              </span>
            )}
            <div className="ml-auto flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-slate-300 transition"
              >
                Close
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-bold transition shadow-lg shadow-[#d4ff00]/10"
              >
                {loading ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SettingsModal;
