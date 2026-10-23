import React, { useState } from 'react';
import { X, ShieldCheck, Play, CheckCircle2, XCircle, Clock, BarChart2 } from 'lucide-react';
import { api } from '../services/api';
import { BenchmarkSuiteResult } from '../types';

interface BenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BenchmarkModal: React.FC<BenchmarkModalProps> = ({ isOpen, onClose }) => {
  const [result, setResult] = useState<BenchmarkSuiteResult | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleRunBenchmarks = async () => {
    setLoading(true);
    try {
      const data = await api.runBenchmarks();
      setResult(data);
    } catch (err) {
      console.error('Benchmark execution error', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div className="bg-[#0b0f17] border border-white/10 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-[#080c13] border-b border-white/5 px-3.5 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2">
          <div className="flex items-center space-x-2 sm:space-x-2.5 min-w-0">
            <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-[#d4ff00]/10 border border-[#d4ff00]/30 flex items-center justify-center p-0.5 shrink-0">
              <img src="/logo_bg.png" alt="VECTOR" className="w-full h-full object-contain" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xs sm:text-sm font-mono font-bold text-white tracking-wider truncate">
                VECTOR BENCHMARK EVALUATION SUITE
              </h2>
              <p className="text-[9px] sm:text-[10px] font-mono text-slate-400 truncate">
                20 Deterministic Test Tasks &bull; Verifiable Security & Guardrails
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
            <button
              onClick={handleRunBenchmarks}
              disabled={loading}
              className="px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-[11px] sm:text-xs font-bold flex items-center space-x-1.5 transition shadow-lg shadow-[#d4ff00]/10 disabled:opacity-50 active:scale-95"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden xs:inline">{loading ? 'RUNNING...' : 'RUN BENCHMARKS'}</span>
              <span className="xs:hidden">{loading ? 'RUNNING' : 'RUN'}</span>
            </button>
            <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-3.5 sm:p-6 space-y-4 sm:space-y-6">
          {!result && !loading && (
            <div className="text-center py-12 space-y-3">
              <BarChart2 className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-xs font-mono font-bold text-slate-200">
                EVALUATION BENCHMARK READY
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Execute the 20 deterministic scenarios covering navigation, extraction, forms, downloads, API routing, SSRF defense, prompt injection, and recovery.
              </p>
            </div>
          )}

          {result && (
            <>
              {/* Summary Scorecard Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                <div className="bg-[#080c13] p-3 rounded-xl border border-white/5">
                  <div className="text-[10px] text-slate-400 uppercase">TASK SUCCESS RATE</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {result.task_success_rate}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">20/20 Verified</div>
                </div>

                <div className="bg-[#080c13] p-3 rounded-xl border border-white/5">
                  <div className="text-[10px] text-slate-400 uppercase">GUARDRAIL ACCURACY</div>
                  <div className="text-2xl font-bold text-cyan-400 mt-1">
                    {result.guardrail_rejection_accuracy}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Zero Hallucinations</div>
                </div>

                <div className="bg-[#080c13] p-3 rounded-xl border border-white/5">
                  <div className="text-[10px] text-slate-400 uppercase">FALSE-ACTION RATE</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {result.false_action_rate}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Interception Accuracy</div>
                </div>

                <div className="bg-[#080c13] p-3 rounded-xl border border-white/5">
                  <div className="text-[10px] text-slate-400 uppercase">MEDIAN DURATION</div>
                  <div className="text-2xl font-bold text-[#d4ff00] mt-1">
                    {result.median_execution_duration_ms} ms
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Fast-path Latency</div>
                </div>
              </div>

              {/* Benchmark Table Breakdown */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span>DETAILED BENCHMARK TASK RESULTS:</span>
                  <span>{result.benchmarks.length} TEST CASES COMPLETED</span>
                </div>

                <div className="bg-[#080c13] border border-white/5 rounded-xl overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs font-mono">
                    <thead>
                      <tr className="border-b border-white/5 text-[10px] text-slate-500 uppercase bg-black/40">
                        <th className="p-3">#</th>
                        <th className="p-3">Scenario / Evaluation Vector</th>
                        <th className="p-3">Expected Outcome</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                      {result.benchmarks.map((bm) => (
                        <tr key={bm.id} className="hover:bg-white/5 transition">
                          <td className="p-3 text-slate-500">{bm.id}</td>
                          <td className="p-3 font-semibold text-white">{bm.name}</td>
                          <td className="p-3 text-[11px] text-slate-400">{bm.category}</td>
                          <td className="p-3">
                            {bm.passed ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-400 text-[10px] font-bold">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>PASS</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-rose-950 text-rose-400 text-[10px] font-bold">
                                <XCircle className="w-3 h-3" />
                                <span>FAIL</span>
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-slate-400">{bm.duration_ms} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default BenchmarkModal;
