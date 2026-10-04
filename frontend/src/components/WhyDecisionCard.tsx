import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Scale } from 'lucide-react';
import { WhyDecision } from '../api/client';

interface WhyDecisionCardProps {
  whyDecision?: WhyDecision;
}

export const WhyDecisionCard: React.FC<WhyDecisionCardProps> = ({ whyDecision }) => {
  const [open, setOpen] = useState(false);

  if (!whyDecision || !whyDecision.policy_rule) {
    return null;
  }

  return (
    <div className="mt-2 rounded-xl border border-sky-900/40 bg-sky-950/20 p-2.5 text-xs">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center space-x-1.5 text-sky-400 hover:text-sky-300 font-semibold focus:outline-none"
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Why this decision?</span>
          <span className="text-[10px] text-slate-400 font-normal ml-1">
            ({whyDecision.final_route || 'Policy Applied'})
          </span>
          {open ? <ChevronUp className="w-3 h-3 ml-1" /> : <ChevronDown className="w-3 h-3 ml-1" />}
        </button>

        <div className="flex items-center space-x-1.5 text-[10px] font-mono text-slate-400">
          <span>conf:</span>
          <span className="text-emerald-400 font-bold">
            {whyDecision.confidence !== undefined ? `${Math.round(whyDecision.confidence * 100)}%` : '100%'}
          </span>
        </div>
      </div>

      {open && (
        <div className="mt-2.5 pt-2 border-t border-sky-900/30 space-y-1.5 text-[11px]">
          <div className="grid grid-cols-3 gap-1 text-[10px] font-mono">
            <div className="p-1 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Intent:</span>
              <span className="text-slate-200 font-medium">{whyDecision.intent || 'unknown'}</span>
            </div>
            <div className="p-1 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Policy Rule:</span>
              <span className="text-sky-300 font-medium truncate block" title={whyDecision.policy_rule}>
                {whyDecision.policy_rule}
              </span>
            </div>
            <div className="p-1 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-500 block">Route Taken:</span>
              <span className="text-emerald-300 font-medium">{whyDecision.final_route}</span>
            </div>
          </div>

          <p className="text-slate-300 leading-relaxed bg-slate-950/40 p-2 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-100">Governing Logic: </span>
            {whyDecision.reason}
          </p>
        </div>
      )}
    </div>
  );
};
