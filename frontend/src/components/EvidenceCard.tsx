import React, { useState } from 'react';
import { ShieldCheck, AlertCircle, ChevronDown, ChevronUp, BookOpen, ExternalLink } from 'lucide-react';
import { Citation } from '../api/client';

interface EvidenceCardProps {
  grounded?: boolean | null;
  citations: Citation[];
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ grounded, citations }) => {
  const [expanded, setExpanded] = useState(false);

  if (grounded === null && (!citations || citations.length === 0)) {
    return null;
  }

  return (
    <div className="mt-2.5 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {grounded ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-800/60 text-emerald-300 font-semibold text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Grounded in Knowledge Base
            </span>
          ) : grounded === false ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-950/80 border border-amber-800/60 text-amber-300 font-semibold text-[11px]">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              Not Fully Grounded / Refused
            </span>
          ) : null}

          {citations.length > 0 && (
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <BookOpen className="w-3 h-3 text-sky-400" />
              {citations.length} Verified {citations.length === 1 ? 'Source' : 'Sources'}
            </span>
          )}
        </div>

        {citations.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium focus:outline-none"
          >
            {expanded ? (
              <>
                Hide Evidence <ChevronUp className="w-3 h-3" />
              </>
            ) : (
              <>
                View Citations <ChevronDown className="w-3 h-3" />
              </>
            )}
          </button>
        )}
      </div>

      {/* Expanded Citations List */}
      {expanded && citations.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-slate-800/80 pt-2.5">
          {citations.map((c, i) => (
            <div key={i} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px]">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-slate-200 flex items-center gap-1">
                  <ExternalLink className="w-3 h-3 text-sky-400" />
                  {c.title || c.source}
                </span>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono">
                    {c.category}
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">
                    relevance: {Math.round(c.score * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-slate-400 leading-relaxed italic line-clamp-2">"{c.snippet}"</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
