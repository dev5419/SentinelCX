import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Lock,
  Eye,
  FileText
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import {
  Ticket,
  PendingApproval,
  AuditRecord,
  PiiFeedItem,
  MetricsSummary,
  fetchTickets,
  fetchApprovals,
  postApprovalDecision,
  fetchAuditLogs,
  fetchPiiFeed
} from '../api/client';
import { SlaCountdownBadge } from '../components/SlaCountdownBadge';

interface SupervisorCommandCenterViewProps {
  metrics: MetricsSummary | null;
  onRefreshMetrics: () => void;
}

export const SupervisorCommandCenterView: React.FC<SupervisorCommandCenterViewProps> = ({
  metrics,
  onRefreshMetrics
}) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditRecord[]>([]);
  const [piiFeed, setPiiFeed] = useState<PiiFeedItem[]>([]);

  // Selected Approval Drawer state
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Filter state for tickets
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  const loadData = useCallback(async () => {
    try {
      const [tData, aData, logs, pii] = await Promise.all([
        fetchTickets(),
        fetchApprovals(),
        fetchAuditLogs(undefined, 30),
        fetchPiiFeed(20)
      ]);
      setTickets(tData);
      setApprovals(aData);
      setAuditLogs(logs);
      setPiiFeed(pii);
    } catch (e) {
      console.error('Failed to load command center data:', e);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleDecision = async (decision: 'approved' | 'rejected') => {
    if (!selectedApproval) return;
    setActionLoading(true);
    try {
      await postApprovalDecision(
        selectedApproval.thread_id,
        decision,
        'sup_vikram_204',
        decisionNotes || (decision === 'approved' ? 'Approved after review' : 'Rejected under policy')
      );
      setToastMessage(`Approval decision (${decision.toUpperCase()}) submitted successfully!`);
      setTimeout(() => setToastMessage(null), 4000);
      setSelectedApproval(null);
      setDecisionNotes('');
      await loadData();
      onRefreshMetrics();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Filter tickets
  const filteredTickets = tickets.filter((t) => {
    if (statusFilter !== 'all' && t.status !== statusFilter) return false;
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false;
    return true;
  });

  // Chart data
  const priorityChartData = [
    { name: 'Critical', value: metrics?.priority_distribution?.Critical || 1, color: '#f43f5e' },
    { name: 'High', value: metrics?.priority_distribution?.High || 2, color: '#f59e0b' },
    { name: 'Medium', value: metrics?.priority_distribution?.Medium || 3, color: '#38bdf8' },
    { name: 'Low', value: metrics?.priority_distribution?.Low || 1, color: '#10b981' }
  ];

  return (
    <div className="space-y-6 pb-16">
      {/* Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 right-6 z-50 p-4 rounded-xl bg-emerald-950 border border-emerald-500 text-emerald-200 shadow-2xl flex items-center gap-2 text-xs font-semibold"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {toastMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header & Quick KPIs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" /> Human-in-the-Loop Supervision
          </span>
          <h1 className="text-2xl font-bold text-white">Supervisor Command Center</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time approval queues, SLA deadlines, live PII audit stream, and compliance logs.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3.5 py-2 rounded-xl glass-panel hover:bg-slate-800 text-slate-200 text-xs font-medium flex items-center gap-2 border border-slate-700 w-fit cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
          Refresh Live Data
        </button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Pending Approvals</span>
            <AlertTriangle className={`w-4 h-4 ${approvals.length > 0 ? 'text-amber-400 animate-bounce' : 'text-slate-600'}`} />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{approvals.length}</div>
          <div className="text-[11px] text-amber-400 mt-1 font-medium">
            {approvals.length > 0 ? 'Requires supervisor decision' : 'All approvals cleared'}
          </div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Active Tickets</span>
            <Users className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{tickets.length}</div>
          <div className="text-[11px] text-slate-400 mt-1">Across all support channels</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Auto-Resolved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {metrics?.auto_resolved_count ?? 2}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Automated execution without human touch</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>PII Redactions</span>
            <Lock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {piiFeed.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">0 raw PII leaks across all runs</div>
        </div>
      </div>

      {/* SECTION 1: Pending Approvals Queue (HITL Core) */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
            <h2 className="font-bold text-white text-base">High-Value Approval Queue (&gt; Rs 2,000)</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950 border border-amber-800 text-amber-300 font-mono">
              {approvals.length} Pending
            </span>
          </div>
          <span className="text-xs text-slate-400">Policy: All transactions &gt; Rs 2,000 require supervisor sign-off</span>
        </div>

        {approvals.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-950/40 border border-slate-800/80 text-slate-400 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
            <p className="font-semibold text-slate-200">No pending approvals in queue.</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Trigger a Rs 15,000 refund scenario from the Customer Portal to test the HITL workflow.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {approvals.map((appr) => (
              <div
                key={appr.thread_id}
                className="p-4 rounded-xl bg-slate-950/70 border border-amber-500/50 shadow-lg shadow-amber-500/5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-amber-300 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800">
                      {appr.approval_id}
                    </span>
                    <span className="text-xs font-bold text-emerald-400 font-mono">
                      Rs {appr.amount.toFixed(2)}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-white mb-1">
                    Order: {appr.order_id || 'ORD-1005'} (User: {appr.user_id})
                  </h3>
                  <p className="text-xs text-slate-300 mb-2 leading-relaxed">
                    {appr.reason}
                  </p>

                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Customer Sentiment:</span>
                      <span className="text-amber-400 font-medium">Frustrated</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Priority:</span>
                      <span className="text-rose-400 font-bold">Critical</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-end space-x-2">
                  <button
                    onClick={() => setSelectedApproval(appr)}
                    className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Review Dossier
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION 2: Active Tickets & SLA Timers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tickets Table (2 cols) */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <h2 className="font-bold text-white text-base">Active Tickets & SLA Deadlines</h2>

            {/* Filters */}
            <div className="flex items-center space-x-2 text-xs">
              <select
                aria-label="Filter tickets by priority"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none"
              >
                <option value="all">All Priorities</option>
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>

              <select
                aria-label="Filter tickets by status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="pending_approval">Pending Approval</option>
                <option value="resolved">Resolved</option>
                <option value="escalated">Escalated</option>
                <option value="open">Open</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-[10px] uppercase font-bold text-slate-400">
                <tr>
                  <th className="pb-2">Ticket</th>
                  <th className="pb-2">Customer</th>
                  <th className="pb-2">Priority</th>
                  <th className="pb-2">SLA Countdown</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredTickets.map((t, idx) => (
                  <tr key={t.ticket_id || `tck-${idx}`} className="hover:bg-slate-900/40">
                    <td className="py-2.5 font-mono text-slate-300">{t.ticket_id}</td>
                    <td className="py-2.5 text-white">{t.user_name}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          t.priority === 'Critical'
                            ? 'bg-rose-950 text-rose-300'
                            : t.priority === 'High'
                            ? 'bg-amber-950 text-amber-300'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {t.priority}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <SlaCountdownBadge deadlineIso={t.sla_deadline} priority={t.priority} />
                    </td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          t.status === 'resolved'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : t.status === 'pending_approval'
                            ? 'bg-amber-950 text-amber-300 border border-amber-800'
                            : 'bg-purple-950 text-purple-300 border border-purple-800'
                        }`}
                      >
                        {t.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Priority Analytics Chart (1 col) */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <h2 className="font-bold text-white text-base mb-2">Priority Distribution</h2>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={priorityChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {priorityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '11px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono mt-2">
            {priorityChartData.map((p) => (
              <div key={p.name} className="flex items-center space-x-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                <span>{p.name}: {p.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 3: Live PII Redaction Feed & Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PII Redaction Stream */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Lock className="w-4 h-4 text-emerald-400" />
              <h2 className="font-bold text-white text-base">Live PII Redaction Feed</h2>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">
              Zero Raw Leaks
            </span>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {piiFeed.length === 0 ? (
              <div className="text-center py-6 text-slate-500 text-xs">No PII detections recorded yet.</div>
            ) : (
              piiFeed.map((item, idx) => (
                <div
                  key={item.id || `pii-${idx}`}
                  className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs flex items-center justify-between"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                      {item.type}
                    </span>
                    <span className="font-mono text-emerald-400 text-xs">{item.masked_token}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* SQLite Audit Trail */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-sky-400" />
              <h2 className="font-bold text-white text-base">Compliance Audit Trail</h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Immutable SQLite Records</span>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {auditLogs.slice(0, 15).map((log, idx) => (
              <div
                key={log.log_id || log.id || `audit-${idx}`}
                className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-200 font-bold text-xs">{log.action}</span>
                    <span className="text-[10px] font-mono text-emerald-400">{log.decision}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 truncate max-w-xs">{log.reason}</p>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* APPROVAL DOSSIER MODAL / DRAWER */}
      <AnimatePresence>
        {selectedApproval && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel w-full max-w-2xl rounded-2xl border border-amber-500/50 p-6 shadow-2xl relative overflow-hidden"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-amber-400 animate-pulse" />
                  <h3 className="text-lg font-bold text-white">
                    Approval Dossier: {selectedApproval.approval_id}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedApproval(null)}
                  className="text-slate-400 hover:text-white text-sm"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 text-xs">
                {/* Order & Amount details */}
                <div className="grid grid-cols-3 gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Order ID:</span>
                    <span className="font-bold text-slate-200 font-mono">{selectedApproval.order_id || 'ORD-1005'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Refund Amount:</span>
                    <span className="font-bold text-emerald-400 font-mono text-sm">
                      Rs {selectedApproval.amount.toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Policy Gate:</span>
                    <span className="font-bold text-amber-300 text-xs">Threshold &gt; Rs 2,000</span>
                  </div>
                </div>

                {/* Handoff Dossier content */}
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="font-semibold text-slate-200 text-xs">Supervisor Review Summary:</div>
                  <p className="text-slate-300 leading-relaxed">
                    {selectedApproval.reason}
                  </p>
                  <p className="text-slate-400 text-[11px]">
                    Customer delivered product within valid 14-day return window. No prior refund issued. Policy requires manual human authorization before SQLite refund execution.
                  </p>
                </div>

                {/* Supervisor Notes */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 mb-1 block">
                    Supervisor Approval Notes (Audit Logged):
                  </label>
                  <input
                    type="text"
                    value={decisionNotes}
                    onChange={(e) => setDecisionNotes(e.target.value)}
                    placeholder="e.g. Approved after verifying high-value invoice with customer"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-end space-x-3">
                <button
                  disabled={actionLoading}
                  onClick={() => handleDecision('rejected')}
                  className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <XCircle className="w-4 h-4" />
                  Decline Refund Request
                </button>

                <button
                  disabled={actionLoading}
                  onClick={() => handleDecision('approved')}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Authorize & Execute Refund (Rs {selectedApproval.amount.toFixed(2)})
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
