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
    <div className="mt-2 rounded-lg border border-[#D6D3D1] bg-[#FAFAF9] p-2.5 text-xs shadow-xs">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center space-x-1.5 text-[#C2410C] hover:text-[#9A3412] font-semibold focus:outline-none cursor-pointer"
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Why this decision?</span>
          <span className="text-[10px] text-[#78716C] font-normal ml-1">
            ({whyDecision.final_route || 'Policy Applied'})
          </span>
          {open ? <ChevronUp className="w-3 h-3 ml-1" /> : <ChevronDown className="w-3 h-3 ml-1" />}
        </button>

        <div className="flex items-center space-x-1.5 text-[10px] font-mono text-[#78716C]">
          <span>conf:</span>
          <span className="text-[#16A34A] font-bold">
            {whyDecision.confidence !== undefined ? `${Math.round(whyDecision.confidence * 100)}%` : '100%'}
          </span>
        </div>
      </div>

      {open && (
        <div className="mt-2.5 pt-2 border-t border-[#D6D3D1] space-y-1.5 text-[11px]">
          <div className="grid grid-cols-3 gap-1 text-[10px] font-mono">
            <div className="p-1.5 rounded-md bg-white border border-[#D6D3D1]">
              <span className="text-[#78716C] block">Intent:</span>
              <span className="text-[#1C1917] font-semibold">{whyDecision.intent || 'unknown'}</span>
            </div>
            <div className="p-1.5 rounded-md bg-white border border-[#D6D3D1]">
              <span className="text-[#78716C] block">Policy Rule:</span>
              <span className="text-[#C2410C] font-semibold truncate block" title={whyDecision.policy_rule}>
                {whyDecision.policy_rule}
              </span>
            </div>
            <div className="p-1.5 rounded-md bg-white border border-[#D6D3D1]">
              <span className="text-[#78716C] block">Route Taken:</span>
              <span className="text-[#16A34A] font-semibold">{whyDecision.final_route}</span>
            </div>
          </div>

          <p className="text-[#57534E] leading-relaxed bg-white p-2 rounded-lg border border-[#D6D3D1]">
            <span className="font-semibold text-[#1C1917]">Governing Logic: </span>
            {whyDecision.reason}
          </p>
        </div>
      )}
    </div>
  );
};
