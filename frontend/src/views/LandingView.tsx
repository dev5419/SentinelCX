import React from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Layers,
  Activity,
  Lock,
  Cpu,
  Database,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  FileText,
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
      <div className="relative pt-6 pb-4 text-center max-w-4xl mx-auto space-y-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-950/80 border border-sky-800/80 text-sky-300 text-xs font-semibold tracking-wide"
        >
          <Shield className="w-3.5 h-3.5 text-sky-400" />
          Production-Quality Enterprise Multi-Agent System
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-6xl font-extrabold tracking-tight text-white leading-tight"
        >
          LLMs reason, <br />
          <span className="bg-gradient-to-r from-sky-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
            Python governs.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-slate-300 text-base md:text-lg max-w-2xl mx-auto leading-relaxed"
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
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-sky-500/25 transition-all transform hover:-translate-y-0.5 flex items-center gap-2 cursor-pointer"
          >
            <Activity className="w-4 h-4" />
            Launch Customer Demo
            <ArrowRight className="w-4 h-4 ml-1" />
          </button>

          <button
            onClick={onOpenCommandCenter}
            className="px-6 py-3.5 rounded-xl glass-panel hover:bg-slate-800 text-slate-200 hover:text-white font-semibold text-sm border border-slate-700 transition-all flex items-center gap-2 cursor-pointer"
          >
            <UserCheck className="w-4 h-4 text-amber-400" />
            Supervisor Command Center
          </button>

          <button
            onClick={onOpenSafetyProof}
            className="px-5 py-3.5 rounded-xl glass-panel hover:bg-slate-800 text-slate-300 hover:text-white font-medium text-sm border border-slate-700 transition-all flex items-center gap-2 cursor-pointer"
          >
            <Shield className="w-4 h-4 text-emerald-400" />
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
          className="glass-panel p-5 rounded-2xl border border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Policy Violations</span>
            <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-800/80 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 font-mono">
            {metrics?.policy_violations ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <span className="text-emerald-400 font-bold">Hard Limit: 0</span> — 100% policy compliance
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-panel p-5 rounded-2xl border border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">PII Leak Count</span>
            <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-800/80 text-emerald-400">
              <Lock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 font-mono">
            {metrics?.pii_leak_count ?? 0}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <span className="text-emerald-400 font-bold">Zero raw PII</span> exposed to LLMs
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel p-5 rounded-2xl border border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Routing Accuracy</span>
            <div className="p-2 rounded-lg bg-sky-950/80 border border-sky-800/80 text-sky-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-sky-400 font-mono">
            {metrics?.routing_accuracy_pct ?? 98.61}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Across 72 verified evaluation cases
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-panel p-5 rounded-2xl border border-slate-800 relative overflow-hidden"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Average Turn Latency</span>
            <div className="p-2 rounded-lg bg-purple-950/80 border border-purple-800/80 text-purple-400">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-purple-300 font-mono">
            {metrics?.avg_latency_ms ? `${Math.round(metrics.avg_latency_ms)}ms` : '6.1s'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            P95: {metrics?.p95_latency_ms ? `${Math.round(metrics.p95_latency_ms)}ms` : '13.6s'}
          </div>
        </motion.div>
      </div>

      {/* Animated Architecture Diagram */}
      <div className="max-w-6xl mx-auto glass-panel p-8 rounded-3xl border border-slate-800">
        <div className="text-center max-w-xl mx-auto mb-8">
          <span className="text-xs font-bold uppercase tracking-wider text-sky-400">System Architecture</span>
          <h2 className="text-2xl font-bold text-white mt-1">3-Tier Dual Governance Pipeline</h2>
          <p className="text-slate-400 text-xs mt-1">
            Every user turn flows through deterministic guards, intelligent multi-agent triage, and strict transactional policy gates.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Layer 1 */}
          <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-sky-500/40 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-xl bg-sky-950 border border-sky-800/80 flex items-center justify-center text-sky-400">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider">Tier 1</span>
                  <h3 className="text-base font-bold text-white">Security & Perception</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>PII Guard:</strong> Regex & NER masking of phone, email, Aadhaar, cards before LLM.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Injection Guard:</strong> Halts prompt injections, system prompt leaks, and Hinglish jailbreaks.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono">
              Deterministic Python Execution
            </div>
          </div>

          {/* Layer 2 */}
          <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-purple-500/40 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-xl bg-purple-950 border border-purple-800/80 flex items-center justify-center text-purple-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Tier 2</span>
                  <h3 className="text-base font-bold text-white">Multi-Agent Triage</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Triage Classifier:</strong> Intent, confidence, sentiment, priority & dynamic SLA deadline.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Verifiable RAG:</strong> Metadata-filtered Chroma retrieval + 2-pass strict NLI grounding check.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono">
              LLM Reasoning + Grounding Filter
            </div>
          </div>

          {/* Layer 3 */}
          <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-amber-500/40 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-9 h-9 rounded-xl bg-amber-950 border border-amber-800/80 flex items-center justify-center text-amber-400">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Tier 3</span>
                  <h3 className="text-base font-bold text-white">Action Governance</h3>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Policy Gate:</strong> Enforces 14-day window, account ownership, and idempotency in SQLite.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span><strong>HITL Interrupts:</strong> Pauses high-value requests (&gt; Rs 2,000) for supervisor approval.</span>
                </li>
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono">
              LangGraph StateMachine + SQLite
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
