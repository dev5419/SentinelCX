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
      return 'border-sky-400 bg-sky-950/70 text-sky-200 shadow-[0_0_20px_rgba(56,189,248,0.6)] animate-pulse';
    }
    if (completedNodes.has(nodeId)) {
      if (nodeId === 'reject') return 'border-rose-500/80 bg-rose-950/40 text-rose-300';
      if (nodeId === 'hitl_interrupt') return 'border-amber-500/80 bg-amber-950/40 text-amber-300';
      if (nodeId === 'auto_execute') return 'border-emerald-500/80 bg-emerald-950/40 text-emerald-300';
      if (nodeId === 'escalate') return 'border-purple-500/80 bg-purple-950/40 text-purple-300';
      return 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200';
    }
    return 'border-slate-800/80 bg-slate-900/40 text-slate-500';
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center space-x-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-sky-400 animate-ping" />
          <h3 className="font-semibold text-slate-100 text-sm tracking-wide flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" />
            LIVE AGENT FLOW
          </h3>
        </div>
        <div className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800/80 text-slate-400 font-mono">
          LangGraph MemorySaver
        </div>
      </div>

      {/* Main Visual Flow Diagram */}
      <div className="flex-1 py-4 overflow-y-auto space-y-4 pr-1">
        {/* Layer 1: Security Shield */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Layer 1: Security & Protection</span>
            <span className="text-slate-500">Deterministic Guardrails</span>
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
                  className={`p-3 rounded-xl border transition-all duration-300 ${getStatusColor(n.id)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-sky-300 animate-spin' : isCompleted ? 'text-emerald-400' : 'text-slate-500'}`} />
                      <span className="text-xs font-semibold">{n.label}</span>
                    </div>
                    {nodeTrace && (
                      <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        {nodeTrace.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] mt-1 opacity-70 truncate">{nodeTrace?.summary || n.sublabel}</p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Arrow connector */}
        <div className="flex justify-center -my-1">
          <div className="w-0.5 h-3 bg-slate-700/60" />
        </div>

        {/* Layer 2: Perception & Triage */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Layer 2: Multi-Agent Triage</span>
            <span className="text-slate-500">LLM Reasoning</span>
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
                className={`p-3 rounded-xl border transition-all duration-300 ${getStatusColor(n.id)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-sky-300 animate-spin' : isCompleted ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span className="text-xs font-semibold">{n.label}</span>
                  </div>
                  {nodeTrace && (
                    <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {nodeTrace.duration_ms}ms
                    </span>
                  )}
                </div>
                <p className="text-[10px] mt-1 opacity-70 truncate">{nodeTrace?.summary || n.sublabel}</p>
              </motion.div>
            );
          })()}
        </div>

        {/* Arrow split */}
        <div className="flex justify-center -my-1">
          <div className="w-0.5 h-3 bg-slate-700/60" />
        </div>

        {/* Layer 3: Conditional Governance Split (Action Policy Gate vs Verifiable RAG) */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Layer 3: Execution Engine</span>
            <span className="text-slate-500">Dual Path Gate</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Column A: Transactional Policy Gate */}
            <div className="space-y-2 p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <span className="text-[10px] font-bold text-sky-400 uppercase tracking-wider">Policy Gate (Orders)</span>
              
              {/* Policy Gate Node */}
              {(() => {
                const n = NODES[3];
                const Icon = n.icon;
                const nodeTrace = getNodeTrace(n.id);
                return (
                  <div className={`p-2 rounded-lg border text-xs ${getStatusColor(n.id)}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-medium flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{n.label}</span>
                      {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                    </div>
                  </div>
                );
              })()}

              {/* Sub-actions */}
              <div className="space-y-1.5 pl-2 border-l border-slate-700/50">
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
                            ? 'border-emerald-500/80 bg-emerald-950/40 text-emerald-300 font-semibold'
                            : n.id === 'hitl_interrupt'
                            ? 'border-amber-500/80 bg-amber-950/50 text-amber-200 font-semibold shadow-[0_0_15px_rgba(245,158,11,0.3)]'
                            : 'border-rose-500/80 bg-rose-950/40 text-rose-300 font-semibold'
                          : 'border-slate-800/40 text-slate-600 bg-slate-900/20'
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
            <div className="space-y-2 p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Verifiable RAG (FAQs)</span>
              
              {/* RAG Node */}
              {(() => {
                const n = NODES[7];
                const Icon = n.icon;
                const nodeTrace = getNodeTrace(n.id);
                return (
                  <div className={`p-2 rounded-lg border text-xs ${getStatusColor(n.id)}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-medium flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{n.label}</span>
                      {nodeTrace && <span className="text-[9px] font-mono">{nodeTrace.duration_ms}ms</span>}
                    </div>
                  </div>
                );
              })()}

              {/* Grounding and Escalate */}
              <div className="space-y-1.5 pl-2 border-l border-slate-700/50">
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
                            ? 'border-emerald-500/80 bg-emerald-950/40 text-emerald-300 font-semibold'
                            : 'border-purple-500/80 bg-purple-950/50 text-purple-200 font-semibold'
                          : 'border-slate-800/40 text-slate-600 bg-slate-900/20'
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
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
            Layer 4: Response Synthesis
          </div>
          {(() => {
            const n = NODES[10]; // respond
            const Icon = n.icon;
            const nodeTrace = getNodeTrace(n.id);
            const isCompleted = completedNodes.has(n.id);
            const isActive = activeNode === n.id;
            return (
              <div className={`p-3 rounded-xl border transition-all duration-300 ${getStatusColor(n.id)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-sky-300 animate-spin' : isCompleted ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span className="text-xs font-semibold">{n.label}</span>
                  </div>
                  {nodeTrace && (
                    <span className="text-[10px] font-mono opacity-80 flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      {nodeTrace.duration_ms}ms
                    </span>
                  )}
                </div>
                <p className="text-[10px] mt-1 opacity-70 truncate">{nodeTrace?.summary || n.sublabel}</p>
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
          className="mt-3 p-3 rounded-xl bg-slate-950/80 border border-sky-900/40 text-xs"
        >
          <div className="flex items-center justify-between text-slate-300 font-semibold mb-1">
            <span className="text-sky-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Decision: {whyDecision.final_route || 'Completed'}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800/60 font-mono">
              conf: {whyDecision.confidence ?? 1.0}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
            <span className="text-slate-300 font-medium">Policy:</span> {whyDecision.policy_rule} — {whyDecision.reason}
          </p>
        </motion.div>
      )}
    </div>
  );
};
