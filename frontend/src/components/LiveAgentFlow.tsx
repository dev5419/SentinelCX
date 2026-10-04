import React from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  Compass,
  FileCheck2,
  CheckCircle2,
  UserCheck,
  XCircle,
  Database,
  Search,
  Send,
  Cpu,
  Clock
} from 'lucide-react';
import { TraceStep, WhyDecision } from '../api/client';

interface LiveAgentFlowProps {
  activeNode: string | null;
  completedNodes: Set<string>;
  trace: TraceStep[];
  whyDecision?: WhyDecision;
  isPendingApproval?: boolean;
}

interface NodeConfig {
  id: string;
  label: string;
  sublabel: string;
  category: 'security' | 'intelligence' | 'governance' | 'output';
  icon: any;
}

const NODES: NodeConfig[] = [
  { id: 'pii', label: 'PII Guard', sublabel: 'Regex & NER Masking', category: 'security', icon: ShieldCheck },
  { id: 'injection', label: 'Injection Guard', sublabel: 'Anti-Jailbreak Filter', category: 'security', icon: AlertTriangle },
  { id: 'triage', label: 'Triage Agent', sublabel: 'Intent, Sentiment, SLA', category: 'intelligence', icon: Compass },
  { id: 'policy_gate', label: 'Policy Gate', sublabel: '14d Window & Eligibility', category: 'governance', icon: FileCheck2 },
  { id: 'auto_execute', label: 'Auto Execution', sublabel: '<= Rs 2,000 Refund', category: 'governance', icon: CheckCircle2 },
  { id: 'hitl_interrupt', label: 'HITL Interrupt', sublabel: '> Rs 2,000 Supervisor Review', category: 'governance', icon: UserCheck },
  { id: 'reject', label: 'Policy Reject', sublabel: 'Ineligible / Expired', category: 'governance', icon: XCircle },
  { id: 'rag', label: 'Verifiable RAG', sublabel: 'Metadata Filtered Retrieval', category: 'intelligence', icon: Database },
  { id: 'grounding', label: 'Strict Grounding', sublabel: '2-Pass NLI Verification', category: 'intelligence', icon: Search },
  { id: 'escalate', label: 'Human Handoff', sublabel: 'Escalation Dossier', category: 'governance', icon: AlertTriangle },
  { id: 'respond', label: 'Response Gate', sublabel: 'Explainability & Citations', category: 'output', icon: Send },
];

export const LiveAgentFlow: React.FC<LiveAgentFlowProps> = ({
  activeNode,
  completedNodes,
  trace,
  whyDecision,
  isPendingApproval,
}) => {
  // Find duration for a node from trace
  const getNodeTrace = (nodeId: string) => {
    return trace.find((t) => t.node === nodeId);
  };

  const getStatusColor = (nodeId: string) => {
    if (activeNode === nodeId) {
      return 'border-[#C2410C] bg-[#FFF7ED] text-[#C2410C] shadow-[0_0_12px_rgba(194,65,12,0.3)] animate-pulse';
    }
    if (completedNodes.has(nodeId)) {
      if (nodeId === 'reject') return 'border-[#DC2626] bg-[#FEF2F2] text-[#DC2626]';
      if (nodeId === 'hitl_interrupt') return 'border-[#F59E0B] bg-[#FFFBEB] text-[#B45309]';
      if (nodeId === 'auto_execute') return 'border-[#16A34A] bg-[#F0FDF4] text-[#16A34A]';
      if (nodeId === 'escalate') return 'border-[#78716C] bg-[#E7E5E4] text-[#1C1917]';
      return 'border-[#16A34A] bg-[#F0FDF4] text-[#16A34A]';
    }
    return 'border-[#D6D3D1] bg-white text-[#78716C]';
  };

  return (
    <div className="bg-[#F5F5F4] rounded-xl p-5 border border-[#D6D3D1] flex flex-col h-full overflow-hidden shadow-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#D6D3D1]">
        <div className="flex items-center space-x-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#C2410C] animate-ping" />
          <h3 className="font-semibold text-[#1C1917] text-sm tracking-wide flex items-center gap-2 font-display">
            <Cpu className="w-4 h-4 text-[#C2410C]" />
            LIVE AGENT FLOW
          </h3>
        </div>
        <div className="text-xs px-2.5 py-0.5 rounded-full bg-[#E7E5E4] border border-[#D6D3D1] text-[#57534E] font-mono font-medium">
          LangGraph MemorySaver
        </div>
      </div>

      {/* Main Visual Flow Diagram */}
      <div className="flex-1 py-4 overflow-y-auto space-y-4 pr-1">
        {/* Layer 1: Security Shield */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#78716C] mb-1.5 flex items-center justify-between">
            <span>Layer 1: Security & Protection</span>
            <span className="text-[#57534E]">Deterministic Guardrails</span>
          </div>
          <div className="grid grid-cols-2 gap-2.5">
            {NODES.slice(0, 2).map((n) => {
              const Icon = n.icon;
              const nodeTrace = getNodeTrace(n.id);
              const isCompleted = completedNodes.has(n.id);
              const isActive = activeNode === n.id;
              return (
                <motion.div
                  key={n.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-3 rounded-lg border transition-all duration-200 ${getStatusColor(n.id)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-[#C2410C] animate-spin' : isCompleted ? 'text-[#16A34A]' : 'text-[#78716C]'}`} />
                      <span className="text-xs font-semibold">{n.label}</span>
                    </div>
                    {nodeTrace && (
                      <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        {nodeTrace.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] mt-1 opacity-80 truncate">{nodeTrace?.summary || n.sublabel}</p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Arrow connector */}
        <div className="flex justify-center -my-1">
          <div className="w-0.5 h-3 bg-[#D6D3D1]" />
        </div>

        {/* Layer 2: Perception & Triage */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#78716C] mb-1.5 flex items-center justify-between">
            <span>Layer 2: Multi-Agent Triage</span>
            <span className="text-[#57534E]">LLM Reasoning</span>
          </div>
          {(() => {
            const n = NODES[2]; // triage
            const Icon = n.icon;
            const nodeTrace = getNodeTrace(n.id);
            const isCompleted = completedNodes.has(n.id);
            const isActive = activeNode === n.id;
            return (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 rounded-lg border transition-all duration-200 ${getStatusColor(n.id)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#C2410C] animate-spin' : isCompleted ? 'text-[#16A34A]' : 'text-[#78716C]'}`} />
                    <span className="text-xs font-semibold">{n.label}</span>
                  </div>
                  {nodeTrace && (
                    <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {nodeTrace.duration_ms}ms
                    </span>
                  )}
                </div>
                <p className="text-[10px] mt-1 opacity-80 truncate">{nodeTrace?.summary || n.sublabel}</p>
              </motion.div>
            );
          })()}
        </div>

        {/* Arrow split */}
        <div className="flex justify-center -my-1">
          <div className="w-0.5 h-3 bg-[#D6D3D1]" />
        </div>

        {/* Layer 3: Conditional Governance Split (Action Policy Gate vs Verifiable RAG) */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#78716C] mb-1.5 flex items-center justify-between">
            <span>Layer 3: Execution Engine</span>
            <span className="text-[#57534E]">Dual Path Gate</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Column A: Transactional Policy Gate */}
            <div className="space-y-2 p-2.5 rounded-lg bg-white border border-[#D6D3D1]">
              <span className="text-[10px] font-bold text-[#C2410C] uppercase tracking-wider">Policy Gate (Orders)</span>
              
              {/* Policy Gate Node */}
              {(() => {
                const n = NODES[3];
                const Icon = n.icon;
                const nodeTrace = getNodeTrace(n.id);
                return (
                  <div className={`p-2 rounded-lg border text-xs ${getStatusColor(n.id)}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{n.label}</span>
                      {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                    </div>
                  </div>
                );
              })()}

              {/* Sub-actions */}
              <div className="space-y-1.5 pl-2 border-l-2 border-[#D6D3D1]">
                {[NODES[4], NODES[5], NODES[6]].map((n) => {
                  const Icon = n.icon;
                  const nodeTrace = getNodeTrace(n.id);
                  const isCurrent = completedNodes.has(n.id) || (n.id === 'hitl_interrupt' && isPendingApproval);
                  return (
                    <div
                      key={n.id}
                      className={`p-1.5 rounded-md border text-[11px] transition-all ${
                        isCurrent
                          ? n.id === 'auto_execute'
                            ? 'border-[#16A34A] bg-[#F0FDF4] text-[#16A34A] font-semibold'
                            : n.id === 'hitl_interrupt'
                            ? 'border-[#F59E0B] bg-[#FFFBEB] text-[#B45309] font-semibold shadow-xs'
                            : 'border-[#DC2626] bg-[#FEF2F2] text-[#DC2626] font-semibold'
                          : 'border-[#D6D3D1] text-[#78716C] bg-[#F5F5F4]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5"><Icon className="w-3 h-3" />{n.label}</span>
                        {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Column B: Knowledge Base RAG */}
            <div className="space-y-2 p-2.5 rounded-lg bg-white border border-[#D6D3D1]">
              <span className="text-[10px] font-bold text-[#F59E0B] uppercase tracking-wider">Verifiable RAG (FAQs)</span>
              
              {/* RAG Node */}
              {(() => {
                const n = NODES[7];
                const Icon = n.icon;
                const nodeTrace = getNodeTrace(n.id);
                return (
                  <div className={`p-2 rounded-lg border text-xs ${getStatusColor(n.id)}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{n.label}</span>
                      {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                    </div>
                  </div>
                );
              })()}

              {/* Grounding and Escalate */}
              <div className="space-y-1.5 pl-2 border-l-2 border-[#D6D3D1]">
                {[NODES[8], NODES[9]].map((n) => {
                  const Icon = n.icon;
                  const nodeTrace = getNodeTrace(n.id);
                  const isCurrent = completedNodes.has(n.id);
                  return (
                    <div
                      key={n.id}
                      className={`p-1.5 rounded-md border text-[11px] transition-all ${
                        isCurrent
                          ? n.id === 'grounding'
                            ? 'border-[#16A34A] bg-[#F0FDF4] text-[#16A34A] font-semibold'
                            : 'border-[#78716C] bg-[#E7E5E4] text-[#1C1917] font-semibold'
                          : 'border-[#D6D3D1] text-[#78716C] bg-[#F5F5F4]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5"><Icon className="w-3 h-3" />{n.label}</span>
                        {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Output Layer */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#78716C] mb-1.5">
            Layer 4: Response Synthesis
          </div>
          {(() => {
            const n = NODES[10]; // respond
            const Icon = n.icon;
            const nodeTrace = getNodeTrace(n.id);
            const isCompleted = completedNodes.has(n.id);
            const isActive = activeNode === n.id;
            return (
              <div className={`p-3 rounded-lg border transition-all duration-200 ${getStatusColor(n.id)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#C2410C] animate-spin' : isCompleted ? 'text-[#16A34A]' : 'text-[#78716C]'}`} />
                    <span className="text-xs font-semibold">{n.label}</span>
                  </div>
                  {nodeTrace && (
                    <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {nodeTrace.duration_ms}ms
                    </span>
                  )}
                </div>
                <p className="text-[10px] mt-1 opacity-80 truncate">{nodeTrace?.summary || n.sublabel}</p>
              </div>
            );
          })()}
        </div>
      </div>

      {/* Decision Summary Footer */}
      {whyDecision && whyDecision.policy_rule && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 p-3 rounded-lg bg-white border border-[#D6D3D1] text-xs shadow-xs"
        >
          <div className="flex items-center justify-between text-[#1C1917] font-semibold mb-1">
            <span className="text-[#C2410C] flex items-center gap-1.5 font-bold">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#16A34A]" /> Decision: {whyDecision.final_route || 'Completed'}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E7E5E4] text-[#57534E] border border-[#D6D3D1] font-mono font-medium">
              conf: {whyDecision.confidence ?? 1.0}
            </span>
          </div>
          <p className="text-[11px] text-[#57534E] line-clamp-2 leading-relaxed">
            <span className="text-[#1C1917] font-semibold">Policy:</span> {whyDecision.policy_rule} — {whyDecision.reason}
          </p>
        </motion.div>
      )}
    </div>
  );
};
