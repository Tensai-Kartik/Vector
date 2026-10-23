import React from 'react';
import { ShieldCheck, Download, FileText, ArrowDownToLine, Database, Clock } from 'lucide-react';
import { ExecutionReport, ArtifactMetadata } from '../types';

interface AuditReportProps {
  report?: ExecutionReport;
  extractedData?: any[];
  artifacts?: ArtifactMetadata[];
  missionId?: string;
}

export const AuditReport: React.FC<AuditReportProps> = ({
  report,
  extractedData = [],
  artifacts = [],
  missionId,
}) => {
  if (!report && extractedData.length === 0 && artifacts.length === 0) {
    return (
      <div className="bg-[#0b0f17] border border-white/10 rounded-2xl p-8 text-center">
        <img src="/logo_bg.png" alt="VECTOR" className="w-12 h-12 object-contain mx-auto mb-3 opacity-60 drop-shadow-[0_0_12px_rgba(212,255,0,0.25)]" />
        <h3 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
          VECTOR Verification & Audit Dossier Standby
        </h3>
        <p className="text-[11px] text-slate-400 max-w-sm mx-auto mt-1">
          When an autonomous mission concludes, independent postcondition proofs, extracted records, and cryptographic artifact checksums will be synthesized here.
        </p>
      </div>
    );
  }

  const downloadJSON = () => {
    const data = JSON.stringify(report || { extractedData, artifacts }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vector_audit_report_${missionId || 'latest'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    if (!extractedData || extractedData.length === 0) return;
    const keys = Object.keys(extractedData[0]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [keys.join(','), ...extractedData.map((row) => keys.map((k) => `"${row[k] || ''}"`).join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `vector_extracted_records_${missionId || 'latest'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const isVerified = report?.is_verified ?? false;

  return (
    <div className="bg-[#0b0f17] border border-white/10 rounded-2xl p-4 sm:p-6 shadow-2xl space-y-4 sm:space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/5 pb-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <img src="/logo_bg.png" alt="VECTOR" className="w-4 h-4 object-contain shrink-0" />
            <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
              VECTOR INDEPENDENT VERIFICATION & AUDIT DOSSIER
            </span>
            <span
              className={`text-[9px] sm:text-[10px] font-mono px-2 py-0.5 rounded-md font-bold uppercase ${
                isVerified
                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                  : 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
              }`}
            >
              {isVerified ? 'VERIFIED OUTCOME' : 'UNVERIFIED / PARTIAL'}
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-400 font-mono mt-1">
            {report?.verification_summary || 'Task completed and verified against DOM state.'}
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {extractedData.length > 0 && (
            <button
              onClick={downloadCSV}
              className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono text-slate-200 hover:text-white flex items-center space-x-1.5 transition active:scale-95"
            >
              <ArrowDownToLine className="w-3.5 h-3.5 text-[#d4ff00]" />
              <span>EXPORT CSV</span>
            </button>
          )}

          <button
            onClick={downloadJSON}
            className="px-3.5 sm:px-4 py-1.5 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-mono text-xs font-bold flex items-center space-x-1.5 transition shadow-lg shadow-[#d4ff00]/10 active:scale-95"
          >
            <Download className="w-3.5 h-3.5" />
            <span>EXPORT DOSSIER</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      {report && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 font-mono">
          <div className="bg-[#080c13] p-2.5 sm:p-3 rounded-xl border border-white/5">
            <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase">Total Steps</span>
            <p className="text-base sm:text-lg font-bold text-white">{report.total_steps}</p>
          </div>
          <div className="bg-[#080c13] p-2.5 sm:p-3 rounded-xl border border-white/5">
            <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase">Verified Passed</span>
            <p className="text-base sm:text-lg font-bold text-emerald-400">{report.completed_steps}</p>
          </div>
          <div className="bg-[#080c13] p-2.5 sm:p-3 rounded-xl border border-white/5">
            <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase">Execution Time</span>
            <p className="text-base sm:text-lg font-bold text-cyan-400">{report.duration_seconds.toFixed(2)}s</p>
          </div>
          <div className="bg-[#080c13] p-2.5 sm:p-3 rounded-xl border border-white/5">
            <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase">Guardrail Blocks</span>
            <p className="text-base sm:text-lg font-bold text-slate-300">{report.guardrail_rejections.length}</p>
          </div>
        </div>
      )}

      {/* Extracted Records Table */}
      {extractedData && extractedData.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-200">
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            <span>EXTRACTED STRUCTURED DATA ({extractedData.length} RECORDS)</span>
          </div>
          <div className="bg-[#080c13] border border-white/5 rounded-xl overflow-x-auto max-h-56 overflow-y-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-[#05070a] text-slate-400 text-[10px] uppercase border-b border-white/5 sticky top-0">
                <tr>
                  {Object.keys(extractedData[0]).map((k) => (
                    <th key={k} className="p-2.5">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300 text-[11px]">
                {extractedData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition">
                    {Object.values(row).map((v: any, cIdx) => (
                      <td key={cIdx} className="p-2.5">
                        {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditReport;
