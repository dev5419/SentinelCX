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
    <div className="mt-2.5 rounded-lg border border-[#D6D3D1] bg-[#FAFAF9] p-3 text-xs shadow-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {grounded ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#F0FDF4] border border-[#16A34A]/30 text-[#16A34A] font-semibold text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#16A34A]" />
              Grounded in Knowledge Base
            </span>
          ) : grounded === false ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#FFFBEB] border border-[#F59E0B]/40 text-[#B45309] font-semibold text-[11px]">
              <AlertCircle className="w-3.5 h-3.5 text-[#F59E0B]" />
              Not Fully Grounded / Refused
            </span>
          ) : null}

          {citations.length > 0 && (
            <span className="text-[11px] text-[#57534E] flex items-center gap-1">
              <BookOpen className="w-3 h-3 text-[#C2410C]" />
              {citations.length} Verified {citations.length === 1 ? 'Source' : 'Sources'}
            </span>
          )}
        </div>

        {citations.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[11px] text-[#C2410C] hover:text-[#9A3412] flex items-center gap-1 font-semibold focus:outline-none cursor-pointer"
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
        <div className="mt-3 space-y-2 border-t border-[#D6D3D1] pt-2.5">
          {citations.map((c, i) => (
            <div key={i} className="p-2.5 rounded-lg bg-white border border-[#D6D3D1] text-[11px]">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-[#1C1917] flex items-center gap-1">
                  <ExternalLink className="w-3 h-3 text-[#C2410C]" />
                  {c.title || c.source}
                </span>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#E7E5E4] text-[#57534E] uppercase font-mono font-medium">
                    {c.category}
                  </span>
                  <span className="text-[10px] font-mono text-[#16A34A] font-bold">
                    relevance: {Math.round(c.score * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-[#57534E] leading-relaxed italic line-clamp-2">"{c.snippet}"</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
