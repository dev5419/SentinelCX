import React from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Activity,
  Lock,
  Cpu,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
  UserCheck,
  Zap
} from 'lucide-react';
import { MetricsSummary } from '../api/client';

interface LandingViewProps {
  metrics: MetricsSummary | null;
  onLaunchDemo: () => void;
  onOpenCommandCenter: () => void;
  onOpenSafetyProof: () => void;
}

export const LandingView: React.FC<LandingViewProps> = ({
  metrics,
  onLaunchDemo,
  onOpenCommandCenter,
  onOpenSafetyProof
}) => {
  return (
    <div className="space-y-10 pb-16">
      {/* Hero Section */}
      <div className="relative pt-8 pb-4 text-center max-w-4xl mx-auto space-y-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E7E5E4] border border-[#D6D3D1] text-[#C2410C] text-xs font-semibold tracking-wide"
        >
          <Shield className="w-3.5 h-3.5 text-[#C2410C]" />
          SentinelCX · Enterprise Multi-Agent System
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-6xl font-bold tracking-tight text-[#1C1917] leading-tight font-display"
        >
          LLMs reason, <br />
          <span className="text-[#C2410C]">
            Python governs.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-[#57534E] text-base md:text-lg max-w-2xl mx-auto leading-relaxed"
        >
          A multi-agent customer support architecture with live execution tracing, deterministic policy gates, zero PII leakage, and Human-in-the-Loop approval workflows.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 pt-4"
        >
          <button
            onClick={onLaunchDemo}
            className="px-6 py-3 rounded-lg bg-[#C2410C] hover:bg-[#9A3412] text-white font-semibold text-sm shadow-md hover:shadow-lg shadow-[#C2410C]/25 transition-all transform hover:-translate-y-0.5 flex items-center gap-2 cursor-pointer"
          >
            <Activity className="w-4 h-4" />
            Launch Customer Demo
            <ArrowRight className="w-4 h-4 ml-1" />
          </button>

          <button
            onClick={onOpenCommandCenter}
            className="px-6 py-3 rounded-lg bg-transparent hover:bg-[#E7E5E4] text-[#1C1917] font-semibold text-sm border border-[#D6D3D1] transition-all flex items-center gap-2 cursor-pointer"
          >
            <UserCheck className="w-4 h-4 text-[#F59E0B]" />
            Supervisor Command Center
          </button>

          <button
            onClick={onOpenSafetyProof}
            className="px-5 py-3 rounded-lg bg-transparent hover:bg-[#E7E5E4] text-[#57534E] hover:text-[#1C1917] font-medium text-sm border border-[#D6D3D1] transition-all flex items-center gap-2 cursor-pointer"
          >
            <Shield className="w-4 h-4 text-[#16A34A]" />
            Safety Proof Matrix
          </button>
        </motion.div>
      </div>

      {/* Live Key Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#78716C]">Policy Violations</span>
            <div className="p-1.5 rounded-md bg-[#E7E5E4] text-[#16A34A]">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold text-[#16A34A] font-mono">
            {metrics?.policy_violations ?? 0}
          </div>
          <div className="text-[11px] text-[#78716C] mt-1 flex items-center gap-1">
            <span className="text-[#16A34A] font-semibold">Hard Limit: 0</span> — 100% compliance
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#78716C]">PII Leak Count</span>
            <div className="p-1.5 rounded-md bg-[#E7E5E4] text-[#16A34A]">
              <Lock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold text-[#16A34A] font-mono">
            {metrics?.pii_leak_count ?? 0}
          </div>
          <div className="text-[11px] text-[#78716C] mt-1 flex items-center gap-1">
            <span className="text-[#16A34A] font-semibold">Zero raw PII</span> exposed to LLMs
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#78716C]">Routing Accuracy</span>
            <div className="p-1.5 rounded-md bg-[#E7E5E4] text-[#C2410C]">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold text-[#C2410C] font-mono">
            {metrics?.routing_accuracy_pct ?? 98.61}%
          </div>
          <div className="text-[11px] text-[#78716C] mt-1">
            Across 72 verified evaluation cases
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#78716C]">Average Latency</span>
            <div className="p-1.5 rounded-md bg-[#E7E5E4] text-[#78716C]">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold text-[#1C1917] font-mono">
            {metrics?.avg_latency_ms ? `${Math.round(metrics.avg_latency_ms)}ms` : '6.1s'}
          </div>
          <div className="text-[11px] text-[#78716C] mt-1">
            P95: {metrics?.p95_latency_ms ? `${Math.round(metrics.p95_latency_ms)}ms` : '13.6s'}
          </div>
        </motion.div>
      </div>

      {/* 3-Tier Dual Governance Pipeline */}
      <div className="max-w-6xl mx-auto bg-[#F5F5F4] p-8 rounded-xl border border-[#D6D3D1] shadow-xs">
        <div className="text-center max-w-xl mx-auto mb-8">
          <span className="text-xs font-bold uppercase tracking-wider text-[#C2410C]">System Architecture</span>
          <h2 className="text-2xl font-bold text-[#1C1917] mt-1 font-display">3-Tier Dual Governance Pipeline</h2>
          <p className="text-[#57534E] text-xs mt-1">
            Every user turn flows through deterministic guards, intelligent multi-agent triage, and strict transactional policy gates.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Layer 1 */}
          <div className="p-6 rounded-xl bg-white border border-[#D6D3D1] border-l-4 border-l-[#C2410C] hover:shadow-md transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-[#F5F5F4] border border-[#D6D3D1] flex items-center justify-center text-[#C2410C]">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-[#C2410C] uppercase tracking-wider">Tier 1</span>
                  <h3 className="text-base font-bold text-[#1C1917] font-display">Security & Perception</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-[#57534E]">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">PII Guard:</strong> Regex & NER masking of phone, email, Aadhaar, cards before LLM.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">Injection Guard:</strong> Halts prompt injections, system prompt leaks, and Hinglish jailbreaks.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-[#D6D3D1] text-[11px] text-[#78716C] font-mono">
              Deterministic Python Execution
            </div>
          </div>

          {/* Layer 2 */}
          <div className="p-6 rounded-xl bg-white border border-[#D6D3D1] border-l-4 border-l-[#F59E0B] hover:shadow-md transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-[#F5F5F4] border border-[#D6D3D1] flex items-center justify-center text-[#F59E0B]">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-[#F59E0B] uppercase tracking-wider">Tier 2</span>
                  <h3 className="text-base font-bold text-[#1C1917] font-display">Multi-Agent Triage</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-[#57534E]">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#F59E0B] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">Triage Classifier:</strong> Intent, confidence, sentiment, priority & dynamic SLA deadline.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#F59E0B] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">Verifiable RAG:</strong> Metadata-filtered Chroma retrieval + 2-pass strict NLI grounding check.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-[#D6D3D1] text-[11px] text-[#78716C] font-mono">
              LLM Reasoning + Grounding Filter
            </div>
          </div>

          {/* Layer 3 */}
          <div className="p-6 rounded-xl bg-white border border-[#D6D3D1] border-l-4 border-l-[#16A34A] hover:shadow-md transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-[#F5F5F4] border border-[#D6D3D1] flex items-center justify-center text-[#16A34A]">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-[#16A34A] uppercase tracking-wider">Tier 3</span>
                  <h3 className="text-base font-bold text-[#1C1917] font-display">Action Governance</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-[#57534E]">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">Policy Gate:</strong> Enforces 14-day window, account ownership, and idempotency in SQLite.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A] flex-shrink-0 mt-0.5" />
                  <span><strong className="text-[#1C1917]">HITL Interrupts:</strong> Pauses high-value requests (&gt; Rs 2,000) for supervisor approval.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-[#D6D3D1] text-[11px] text-[#78716C] font-mono">
              LangGraph StateMachine + SQLite
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
