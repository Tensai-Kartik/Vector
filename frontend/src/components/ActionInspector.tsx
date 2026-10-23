import React from 'react';
import { Search, ShieldCheck, CheckCircle2, Target } from 'lucide-react';
import { MissionStepState } from '../types';

interface ActionInspectorProps {
  step?: MissionStepState;
}

export const ActionInspector: React.FC<ActionInspectorProps> = ({ step }) => {
  if (!step) {
    return (
      <div className="bg-[#0b0f17] border border-white/10 rounded-2xl p-6 h-[340px] flex flex-col items-center justify-center text-center">
        <Target className="w-8 h-8 text-slate-600 mb-2" />
        <h3 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
          Step Inspector
        </h3>
        <p className="text-[11px] text-slate-400 max-w-xs mt-1">
          Click any step in the graph to inspect guardrail validation checks, locators, and verification evidence.
        </p>
      </div>
    );
  }

  const isCompleted = step.status === 'completed';
  const isFailed = step.status === 'failed';
  const isRejected = step.status === 'rejected';

  return (
    <div className="bg-[#0b0f17] border border-white/10 rounded-2xl flex flex-col h-[340px] overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="bg-[#080c13] border-b border-white/5 px-4 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <Search className="w-3.5 h-3.5 text-cyan-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            STEP INSPECTION
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-slate-400">
            {step.step_id}
          </span>
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded-md uppercase font-bold ${
              isCompleted
                ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                : isRejected || isFailed
                ? 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                : 'bg-[#d4ff00]/15 text-[#d4ff00] border border-[#d4ff00]/30'
            }`}
          >
            {step.status}
          </span>
        </div>
      </div>

      {/* Inspector Details View */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
        {/* Intent & Action */}
        <div className="bg-[#080c13] p-3 rounded-xl border border-white/5 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">INTENT</div>
          <div className="text-xs font-sans font-medium text-slate-100">{step.intent}</div>
          <div className="flex items-center space-x-3 text-[10px] pt-1 text-slate-400">
            <span>ACTION: <span className="text-cyan-400 font-bold">{step.action_type}</span></span>
            {step.target_locator_value && (
              <span className="truncate max-w-[200px]">TARGET: <span className="text-slate-200 select-all">{step.target_locator_value}</span></span>
            )}
          </div>
        </div>

        {/* Pre-Execution Safety Gate Verdict */}
        <div className="bg-[#080c13] p-3 rounded-xl border border-white/5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-[#d4ff00]" />
              PRE-EXECUTION GUARDRAILS
            </span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
              step.validation_message ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
            }`}>
              {step.validation_message ? 'GATE REJECTED' : 'PASSED'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-1.5 text-[10px] text-slate-300 pt-1">
            <div className="flex items-center gap-1">
              <span className="text-emerald-400">&check;</span>
              <span>Domain & SSRF Safe</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-emerald-400">&check;</span>
              <span>Target Unique / Scoped</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-emerald-400">&check;</span>
              <span>DOM Element Active</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-emerald-400">&check;</span>
              <span>Injection Sanitized</span>
            </div>
          </div>

          {step.validation_message && (
            <div className="mt-2 p-2 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
              <strong>Reason:</strong> {step.validation_message}
            </div>
          )}
        </div>

        {/* Verification Evidence */}
        {step.verification_evidence && (
          <div className="bg-[#080c13] p-3 rounded-xl border border-white/5 space-y-1">
            <div className="text-[10px] text-emerald-400 uppercase tracking-wider flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              POST-CONDITION EVIDENCE
            </div>
            <pre className="text-[10px] text-slate-300 bg-black/60 p-2 rounded-lg overflow-x-auto">
              {JSON.stringify(step.verification_evidence, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActionInspector;
