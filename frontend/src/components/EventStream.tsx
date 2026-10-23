import React, { useState, useRef, useEffect } from 'react';
import { Terminal, ChevronDown, ChevronRight } from 'lucide-react';
import { MissionEvent, EventCategory } from '../types';

interface EventStreamProps {
  events: MissionEvent[];
}

export const EventStream: React.FC<EventStreamProps> = ({ events }) => {
  const [filterMode, setFilterMode] = useState<'all' | 'actions' | 'security'>('all');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const filteredEvents = events.filter((e) => {
    if (filterMode === 'all') return true;
    if (filterMode === 'actions') return e.category === 'browser' || e.category === 'api' || e.category === 'verification';
    if (filterMode === 'security') return e.category === 'guardrail' || e.category === 'recovery';
    return true;
  });

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const getCategoryColor = (cat: EventCategory) => {
    switch (cat) {
      case 'browser':
        return 'text-sky-400 bg-sky-950/40 border-sky-800/40';
      case 'api':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-800/40';
      case 'guardrail':
        return 'text-amber-400 bg-amber-950/40 border-amber-800/40';
      case 'verification':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40';
      case 'recovery':
        return 'text-purple-400 bg-purple-950/40 border-purple-800/40';
      case 'artifact':
        return 'text-[#d4ff00] bg-lime-950/40 border-lime-800/40';
      default:
        return 'text-slate-400 bg-slate-900 border-slate-800';
    }
  };

  return (
    <div className="bg-[#0b0f17] border border-white/10 rounded-2xl flex flex-col h-[340px] overflow-hidden shadow-2xl">
      {/* Header & Controls */}
      <div className="bg-[#080c13] border-b border-white/5 px-4 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <Terminal className="w-3.5 h-3.5 text-[#d4ff00]" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            LOG STREAM
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-slate-400">
            {events.length}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <div className="flex items-center bg-white/5 p-0.5 rounded-lg border border-white/5 text-[10px] font-mono">
            <button
              onClick={() => setFilterMode('all')}
              className={`px-2 py-0.5 rounded-md transition ${
                filterMode === 'all'
                  ? 'bg-[#d4ff00] text-black font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterMode('actions')}
              className={`px-2 py-0.5 rounded-md transition ${
                filterMode === 'actions'
                  ? 'bg-cyan-400 text-black font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Actions
            </button>
            <button
              onClick={() => setFilterMode('security')}
              className={`px-2 py-0.5 rounded-md transition ${
                filterMode === 'security'
                  ? 'bg-amber-400 text-black font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Guardrails
            </button>
          </div>

          <label className="flex items-center space-x-1 text-[10px] font-mono text-slate-400 select-none cursor-pointer pl-1">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-black border-white/20 text-[#d4ff00] focus:ring-[#d4ff00] h-3 w-3"
            />
            <span>Scroll</span>
          </label>
        </div>
      </div>

      {/* Event Stream Log Items */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 space-y-1.5 font-mono text-xs select-text"
      >
        {filteredEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-[11px]">
            Awaiting system dispatch events...
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const isExpanded = expandedEventId === ev.id;
            const timeStr = ev.timestamp ? ev.timestamp.split('T')[1]?.substring(0, 8) || ev.timestamp.substring(11, 19) : '--:--:--';
            const hasDetails = ev.details && Object.keys(ev.details).length > 0;

            return (
              <div
                key={ev.id}
                className="bg-[#080c13] hover:bg-[#0c121d] border border-white/5 rounded-xl p-2.5 transition text-[11px]"
              >
                <div
                  className="flex items-start justify-between gap-2 cursor-pointer"
                  onClick={() => hasDetails && setExpandedEventId(isExpanded ? null : ev.id)}
                >
                  <div className="flex items-start space-x-2 overflow-hidden">
                    <span className="text-slate-500 text-[10px] shrink-0 pt-0.5">
                      {timeStr}
                    </span>
                    <span
                      className={`text-[9px] uppercase px-1.5 py-0.5 rounded-md border font-semibold shrink-0 ${getCategoryColor(
                        ev.category
                      )}`}
                    >
                      {ev.category}
                    </span>
                    <span className="text-slate-200 truncate">{ev.message}</span>
                  </div>

                  {hasDetails && (
                    <button className="text-slate-500 hover:text-white shrink-0 pt-0.5">
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>

                {isExpanded && ev.details && (
                  <div className="mt-2 pt-2 border-t border-white/5">
                    <pre className="text-[10px] text-slate-300 bg-black/60 p-2 rounded-lg overflow-x-auto">
                      {JSON.stringify(ev.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default EventStream;
