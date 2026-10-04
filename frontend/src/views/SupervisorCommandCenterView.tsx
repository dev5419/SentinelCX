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

  // Completed decisions live in history, separate from the pending queue.
  const [historyTab, setHistoryTab] = useState<'approved' | 'rejected'>('approved');
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

  // Real-time optimistic approval / rejection handler
  const handleDecision = async (
    targetApproval: PendingApproval,
    decision: 'approved' | 'rejected',
    notes?: string
  ) => {
    setActionLoading(true);
    const nowIso = new Date().toISOString();
    const resolvedNotes =
      notes ||
      (decision === 'approved'
        ? 'Approved after supervisor review'
        : 'Declined under policy by supervisor');

    // 1. Optimistic Real-Time UI Update across state immediately
    setApprovals((prev) =>
      prev.map((item) => {
        if (
          item.thread_id === targetApproval.thread_id ||
          item.approval_id === targetApproval.approval_id
        ) {
          return {
            ...item,
            status: decision,
            decision: decision,
            supervisor_id: 'sup_vikram_204',
            decision_notes: resolvedNotes,
            decided_at: nowIso
          };
        }
        return item;
      })
    );

    setTickets((prev) =>
      prev.map((t) => {
        if (t.thread_id === targetApproval.thread_id) {
          return {
            ...t,
            status: decision === 'approved' ? 'resolved' : 'rejected',
            action: decision === 'approved' ? 'answer' : 'reject',
            updated_at: nowIso
          };
        }
        return t;
      })
    );

    setToastMessage(`Request ${targetApproval.approval_id} ${decision.toUpperCase()} in real time!`);
    setTimeout(() => setToastMessage(null), 4000);

    if (selectedApproval?.thread_id === targetApproval.thread_id) {
      setSelectedApproval(null);
      setDecisionNotes('');
    }

    // 2. Synchronize with backend API
    try {
      await postApprovalDecision(
        targetApproval.thread_id,
        decision,
        'sup_vikram_204',
        resolvedNotes
      );
      await loadData();
      onRefreshMetrics();
    } catch (e: any) {
      console.error('Failed to submit approval decision:', e);
      // Rollback on failure
      await loadData();
      alert(`Error submitting decision: ${e.message}`);
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
  const completedApprovals = approvals.filter((a) => a.status === historyTab);
  const approvedApprovalsCount = approvals.filter((a) => a.status === 'approved').length;
  const rejectedApprovalsCount = approvals.filter((a) => a.status === 'rejected').length;

  // Chart data with Ember Studio color palette
  const priorityChartData = [
    { name: 'Critical', value: metrics?.priority_distribution?.Critical ?? 0, color: '#DC2626' },
    { name: 'High', value: metrics?.priority_distribution?.High ?? 0, color: '#D97706' },
    { name: 'Medium', value: metrics?.priority_distribution?.Medium ?? 0, color: '#C2410C' },
    { name: 'Low', value: metrics?.priority_distribution?.Low ?? 0, color: '#16A34A' }
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
            className="fixed top-20 right-6 z-50 p-4 rounded-xl bg-[#F0FDF4] border border-[#16A34A] text-[#16A34A] shadow-xl flex items-center gap-2 text-xs font-semibold"
          >
            <CheckCircle2 className="w-4 h-4 text-[#16A34A]" />
            {toastMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header & Quick KPIs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold text-[#C2410C] uppercase tracking-wider flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-[#C2410C]" /> Human-in-the-Loop Supervision
          </span>
          <h1 className="text-2xl font-bold text-[#1C1917] font-display">Supervisor Command Center</h1>
          <p className="text-xs text-[#57534E] mt-0.5">
            Real-time approval queues, SLA deadlines, live PII audit stream, and compliance logs.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3.5 py-2 rounded-lg bg-white hover:bg-[#E7E5E4] text-[#1C1917] text-xs font-semibold flex items-center gap-2 border border-[#D6D3D1] w-fit cursor-pointer shadow-xs transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#C2410C]" />
          Refresh Live Data
        </button>
      </div>

      {/* KPI Cards Row */}
      {(() => {
        const pendingApprovalsCount = approvals.filter(
          (a) => (a.status || 'pending') === 'pending'
        ).length;
        const filteredApprovals = approvals.filter((a) => (a.status || 'pending') === 'pending');

        return (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#F5F5F4] p-4 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden">
                <div className="flex items-center justify-between text-xs text-[#78716C] mb-1 font-semibold">
                  <span>Pending Approvals</span>
                  <AlertTriangle
                    className={`w-4 h-4 ${
                      pendingApprovalsCount > 0 ? 'text-[#F59E0B] animate-bounce' : 'text-[#78716C]'
                    }`}
                  />
                </div>
                <div className="text-2xl font-bold text-[#1C1917] font-mono">{pendingApprovalsCount}</div>
                <div className="text-[11px] text-[#D97706] mt-1 font-semibold">
                  {pendingApprovalsCount > 0
                    ? `${pendingApprovalsCount} awaiting supervisor decision`
                    : 'All approvals cleared'}
                </div>
              </div>

              <div className="bg-[#F5F5F4] p-4 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden">
                <div className="flex items-center justify-between text-xs text-[#78716C] mb-1 font-semibold">
                  <span>Active Tickets</span>
                  <Users className="w-4 h-4 text-[#C2410C]" />
                </div>
                <div className="text-2xl font-bold text-[#1C1917] font-mono">{tickets.length}</div>
                <div className="text-[11px] text-[#78716C] mt-1">Across all support channels</div>
              </div>

              <div className="bg-[#F5F5F4] p-4 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden">
                <div className="flex items-center justify-between text-xs text-[#78716C] mb-1 font-semibold">
                  <span>Auto-Resolved</span>
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A]" />
                </div>
                <div className="text-2xl font-bold text-[#16A34A] font-mono">
                  {metrics?.auto_resolved_count ?? 2}
                </div>
                <div className="text-[11px] text-[#78716C] mt-1">Automated execution without human touch</div>
              </div>

              <div className="bg-[#F5F5F4] p-4 rounded-xl border border-[#D6D3D1] shadow-xs relative overflow-hidden">
                <div className="flex items-center justify-between text-xs text-[#78716C] mb-1 font-semibold">
                  <span>PII Redactions</span>
                  <Lock className="w-4 h-4 text-[#16A34A]" />
                </div>
                <div className="text-2xl font-bold text-[#16A34A] font-mono">
                  {piiFeed.length}
                </div>
                <div className="text-[11px] text-[#78716C] mt-1">0 raw PII leaks across all runs</div>
              </div>
            </div>

            {/* SECTION 1: Approval & Human Escalation Command Queue */}
            <div className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B] animate-pulse" />
                  <h2 className="font-bold text-[#1C1917] text-base font-display">Human Supervision & Approval Queue</h2>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[#E7E5E4] border border-[#D6D3D1] text-[#B45309] font-mono font-semibold">
                    {pendingApprovalsCount} Pending
                  </span>
                </div>

              </div>

              {filteredApprovals.length === 0 ? (
                <div className="p-8 text-center rounded-xl bg-white border border-[#D6D3D1] text-[#78716C] text-xs">
                  <CheckCircle2 className="w-8 h-8 text-[#16A34A] mx-auto mb-2 opacity-80" />
                  <p className="font-semibold text-[#1C1917]">
                    No pending requests in the approval queue.
                  </p>
                  <p className="text-[11px] text-[#78716C] mt-1">
                    Completed decisions are available in Approved &amp; Rejected Actions below.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredApprovals.map((appr) => {
                    const isPending = (appr.status || 'pending') === 'pending';
                    const isApproved = appr.status === 'approved';
                    const isRejected = appr.status === 'rejected';

                    const stripeBorder = isApproved
                      ? 'border-l-4 border-l-[#16A34A]'
                      : isRejected
                      ? 'border-l-4 border-l-[#DC2626]'
                      : 'border-l-4 border-l-[#F59E0B]';

                    return (
                      <div
                        key={appr.approval_id || appr.thread_id}
                        className={`p-4 rounded-xl bg-white border border-[#D6D3D1] ${stripeBorder} shadow-xs hover:shadow-md transition-all flex flex-col justify-between`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`font-mono text-xs font-bold px-2 py-0.5 rounded-full border ${
                                  isApproved
                                    ? 'text-[#16A34A] bg-[#F0FDF4] border-[#16A34A]/30'
                                    : isRejected
                                    ? 'text-[#DC2626] bg-[#FEF2F2] border-[#DC2626]/30'
                                    : 'text-[#B45309] bg-[#FFFBEB] border-[#F59E0B]/40'
                                }`}
                              >
                                {appr.approval_id}
                              </span>
                              <span className="text-[10px] uppercase font-bold text-[#57534E] px-2 py-0.5 rounded-full bg-[#E7E5E4] border border-[#D6D3D1]">
                                {appr.type === 'escalation' ? 'Human Escalation' : 'Refund Approval'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {appr.amount > 0 && (
                                <span className="text-xs font-bold text-[#16A34A] font-mono">
                                  Rs {appr.amount.toFixed(2)}
                                </span>
                              )}
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                                  isApproved
                                    ? 'bg-[#F0FDF4] text-[#16A34A] border border-[#16A34A]/30'
                                    : isRejected
                                    ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#DC2626]/30'
                                    : 'bg-[#FFFBEB] text-[#B45309] border border-[#F59E0B]/40'
                                }`}
                              >
                                {isApproved && <CheckCircle2 className="w-3 h-3 text-[#16A34A]" />}
                                {isRejected && <XCircle className="w-3 h-3 text-[#DC2626]" />}
                                {isPending && <span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B] animate-pulse" />}
                                {isApproved ? 'APPROVED' : isRejected ? 'REJECTED' : 'PENDING'}
                              </span>
                            </div>
                          </div>

                          <h3 className="text-sm font-semibold text-[#1C1917] mb-1 font-display">
                            Order: {appr.order_id || 'General Support'} {appr.user_name ? `• ${appr.user_name}` : `(${appr.user_id})`}
                          </h3>
                          <p className="text-xs text-[#57534E] mb-2 leading-relaxed">
                            {appr.reason}
                          </p>

                          {/* Metadata & Decision Notes */}
                          <div className="p-2.5 rounded-lg bg-[#F5F5F4] border border-[#D6D3D1] text-[11px] text-[#57534E] space-y-1">
                            {appr.why_decision?.intent && (
                              <div className="flex justify-between">
                                <span>Intent Route:</span>
                                <span className="text-[#C2410C] font-semibold">{appr.why_decision.intent}</span>
                              </div>
                            )}
                            {isPending && (
                              <div className="flex justify-between">
                                <span>Status:</span>
                                <span className="text-[#D97706] font-semibold">Awaiting Supervisor Action</span>
                              </div>
                            )}
                            {appr.decision_notes && (
                              <div className="pt-1 mt-1 border-t border-[#D6D3D1] text-[#1C1917]">
                                <span className="text-[#78716C] font-semibold block text-[10px]">
                                  {isApproved ? 'Authorization Audit Note:' : 'Decline Reason:'}
                                </span>
                                <span className={isApproved ? 'text-[#16A34A] font-semibold' : 'text-[#DC2626] font-semibold'}>
                                  {appr.decision_notes}
                                </span>
                                {appr.supervisor_id && (
                                  <span className="text-[10px] text-[#78716C] block mt-0.5 font-mono">
                                    By: {appr.supervisor_id} {appr.decided_at && `• ${new Date(appr.decided_at).toLocaleTimeString()}`}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-[#D6D3D1] flex items-center justify-between">
                          <span className="text-[10px] text-[#78716C] font-mono">
                            {appr.created_at ? new Date(appr.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                          </span>

                          <div className="flex items-center gap-2">
                            {isPending ? (
                              <>
                                <button
                                  disabled={actionLoading}
                                  onClick={() => handleDecision(appr, 'approved', 'Quick approved by supervisor')}
                                  className="px-2.5 py-1.5 rounded-lg bg-[#16A34A] hover:bg-[#15803D] text-white text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                                  title="Quick Approve this request"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Approve
                                </button>
                                <button
                                  disabled={actionLoading}
                                  onClick={() => handleDecision(appr, 'rejected', 'Declined under policy by supervisor')}
                                  className="px-2.5 py-1.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                                  title="Reject this request"
                                >
                                  <XCircle className="w-3.5 h-3.5" />
                                  Reject
                                </button>
                                <button
                                  onClick={() => setSelectedApproval(appr)}
                                  className="px-2.5 py-1.5 rounded-lg bg-[#F5F5F4] hover:bg-[#E7E5E4] text-[#C2410C] text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer border border-[#D6D3D1]"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                  Dossier
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => setSelectedApproval(appr)}
                                className="px-2.5 py-1.5 rounded-lg bg-[#F5F5F4] hover:bg-[#E7E5E4] text-[#1C1917] text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer border border-[#D6D3D1]"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                View Details
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        );
      })()}

      {/* SECTION 2: Active Tickets & SLA Timers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tickets Table (2 cols) */}
        <div className="lg:col-span-2 bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <h2 className="font-bold text-[#1C1917] text-base font-display">Active Tickets & SLA Deadlines</h2>

            {/* Filters */}
            <div className="flex items-center space-x-2 text-xs">
              <select
                aria-label="Filter tickets by priority"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-white border border-[#D6D3D1] rounded-lg px-2.5 py-1 text-[#1C1917] focus:outline-none"
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
                className="bg-white border border-[#D6D3D1] rounded-lg px-2.5 py-1 text-[#1C1917] focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="pending_approval">Pending Approval</option>
                <option value="resolved">Resolved</option>
                <option value="rejected">Rejected</option>
                <option value="escalated">Escalated</option>
                <option value="open">Open</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto bg-white border border-[#D6D3D1] rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#D6D3D1] bg-[#F5F5F4] text-[10px] uppercase font-bold text-[#78716C]">
                <tr>
                  <th className="py-2.5 px-3">Ticket</th>
                  <th className="py-2.5 px-3">Customer</th>
                  <th className="py-2.5 px-3">Priority</th>
                  <th className="py-2.5 px-3">SLA Countdown</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#D6D3D1] font-medium">
                {filteredTickets.map((t, idx) => (
                  <tr key={t.ticket_id || `tck-${idx}`} className="hover:bg-[#F5F5F4] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-[#57534E]">{t.ticket_id}</td>
                    <td className="py-2.5 px-3 text-[#1C1917] font-semibold">{t.user_name}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          t.priority === 'Critical'
                            ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#DC2626]/30'
                            : t.priority === 'High'
                            ? 'bg-[#FFFBEB] text-[#B45309] border border-[#F59E0B]/40'
                            : 'bg-[#E7E5E4] text-[#57534E]'
                        }`}
                      >
                        {t.priority}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <SlaCountdownBadge deadlineIso={t.sla_deadline} priority={t.priority} />
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          t.status === 'resolved'
                            ? 'bg-[#F0FDF4] text-[#16A34A] border border-[#16A34A]/30'
                            : t.status === 'pending_approval'
                            ? 'bg-[#FFFBEB] text-[#B45309] border border-[#F59E0B]/40'
                            : 'bg-[#E7E5E4] text-[#57534E] border border-[#D6D3D1]'
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
        <div className="bg-[#F5F5F4] p-4 rounded-xl border border-[#D6D3D1] shadow-xs self-start min-w-0">
          <h2 className="font-bold text-[#1C1917] text-base mb-3 font-display">Priority Distribution</h2>
          <div className="flex items-center gap-4">
            <div className="h-32 w-32 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={priorityChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={56}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {priorityChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#D6D3D1',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: '#1C1917',
                      boxShadow: '0 4px 16px rgba(28,25,23,0.06)'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-2 text-[11px] font-mono">
              {priorityChartData.map((p) => (
                <div key={p.name} className="flex items-center space-x-1.5 text-[#57534E]">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                  <span>{p.name}: {p.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <section aria-label="Completed Human Actions" className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h2 className="font-bold text-[#1C1917] text-base font-display">Approved &amp; Rejected Actions</h2>
          <div className="flex items-center gap-1 p-1 rounded-lg bg-[#E7E5E4] border border-[#D6D3D1] text-xs">
            <button
              onClick={() => setHistoryTab('approved')}
              aria-pressed={historyTab === 'approved'}
              className={`px-3 py-1 rounded-md font-semibold cursor-pointer ${historyTab === 'approved' ? 'bg-[#16A34A] text-white shadow-xs' : 'text-[#16A34A]'}`}
            >
              Approved ({approvedApprovalsCount})
            </button>
            <button
              onClick={() => setHistoryTab('rejected')}
              aria-pressed={historyTab === 'rejected'}
              className={`px-3 py-1 rounded-md font-semibold cursor-pointer ${historyTab === 'rejected' ? 'bg-[#DC2626] text-white shadow-xs' : 'text-[#DC2626]'}`}
            >
              Rejected ({rejectedApprovalsCount})
            </button>
          </div>
        </div>
        {completedApprovals.length === 0 ? (
          <p className="text-xs text-[#78716C] p-4 bg-white rounded-lg border border-[#D6D3D1]">No {historyTab} actions yet.</p>
        ) : (
          <div className="overflow-x-auto bg-white border border-[#D6D3D1] rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#D6D3D1] bg-[#F5F5F4] text-[10px] uppercase font-bold text-[#78716C]">
                <tr>
                  <th className="py-2.5 px-3">Request / Order</th>
                  <th className="py-2.5 px-3">Customer</th>
                  <th className="py-2.5 px-3">Decision Notes</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#D6D3D1]">
                {completedApprovals.map((approval) => (
                  <tr key={approval.approval_id || approval.thread_id}>
                    <td className="py-2.5 px-3 font-mono text-[#57534E]">
                      {approval.approval_id}<span className="block text-[10px]">{approval.order_id || 'General Support'}</span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-[#1C1917]">{approval.user_name || approval.user_id}</td>
                    <td className="py-2.5 px-3 text-[#57534E]">{approval.decision_notes || approval.reason}</td>
                    <td className={`py-2.5 px-3 font-semibold ${approval.status === 'approved' ? 'text-[#16A34A]' : 'text-[#DC2626]'}`}>
                      {approval.status?.toUpperCase()}
                    </td>
                    <td className="py-2.5 px-3">
                      <button onClick={() => setSelectedApproval(approval)} className="text-[#C2410C] font-semibold cursor-pointer flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5" /> View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* SECTION 3: Live PII Redaction Feed & Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PII Redaction Stream */}
        <div className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Lock className="w-4 h-4 text-[#16A34A]" />
              <h2 className="font-bold text-[#1C1917] text-base font-display">Live PII Redaction Feed</h2>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#F0FDF4] text-[#16A34A] border border-[#16A34A]/30 font-mono font-semibold">
              Zero Raw Leaks
            </span>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {piiFeed.length === 0 ? (
              <div className="text-center py-6 text-[#78716C] text-xs">No PII detections recorded yet.</div>
            ) : (
              piiFeed.map((item, idx) => (
                <div
                  key={item.id || `pii-${idx}`}
                  className="p-2.5 rounded-lg bg-white border border-[#D6D3D1] text-xs flex items-center justify-between shadow-2xs"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#E7E5E4] text-[#57534E] font-bold">
                      {item.type}
                    </span>
                    <span className="font-mono text-[#16A34A] font-semibold text-xs">{item.masked_token}</span>
                  </div>
                  <span className="text-[10px] text-[#78716C] font-mono">
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* SQLite Audit Trail */}
        <div className="bg-[#F5F5F4] p-5 rounded-xl border border-[#D6D3D1] shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-[#C2410C]" />
              <h2 className="font-bold text-[#1C1917] text-base font-display">Compliance Audit Trail</h2>
            </div>
            <span className="text-[10px] font-mono text-[#78716C]">Immutable SQLite Records</span>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {auditLogs.slice(0, 15).map((log, idx) => (
              <div
                key={log.log_id || log.id || `audit-${idx}`}
                className="p-2.5 rounded-lg bg-white border border-[#D6D3D1] text-xs flex items-center justify-between shadow-2xs"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[#1C1917] font-bold text-xs">{log.action}</span>
                    <span className="text-[10px] font-mono text-[#16A34A] font-semibold">{log.decision}</span>
                  </div>
                  <p className="text-[11px] text-[#57534E] truncate max-w-xs">{log.reason}</p>
                </div>
                <span className="text-[10px] text-[#78716C] font-mono">
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
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#F5F5F4] w-full max-w-2xl rounded-xl border border-[#D6D3D1] p-6 shadow-2xl relative overflow-hidden"
            >
              <div className="flex items-center justify-between border-b border-[#D6D3D1] pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-[#F59E0B] animate-pulse" />
                  <h3 className="text-lg font-bold text-[#1C1917] font-display">
                    Approval Dossier: {selectedApproval.approval_id}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedApproval(null)}
                  className="text-[#78716C] hover:text-[#1C1917] text-sm cursor-pointer p-1 rounded-md hover:bg-[#E7E5E4]"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 text-xs">
                {/* Order & Amount details */}
                <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-white border border-[#D6D3D1]">
                  <div>
                    <span className="text-[#78716C] block text-[10px]">Order ID:</span>
                    <span className="font-bold text-[#1C1917] font-mono">{selectedApproval.order_id || 'ORD-1005'}</span>
                  </div>
                  <div>
                    <span className="text-[#78716C] block text-[10px]">Refund Amount:</span>
                    <span className="font-bold text-[#16A34A] font-mono text-sm">
                      Rs {selectedApproval.amount.toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#78716C] block text-[10px]">Policy Gate:</span>
                    <span className="font-bold text-[#D97706] text-xs">Threshold &gt; Rs 2,000</span>
                  </div>
                </div>

                {/* Handoff Dossier content */}
                <div className="p-3 rounded-lg bg-white border border-[#D6D3D1] space-y-2">
                  <div className="font-semibold text-[#1C1917] text-xs">Supervisor Review Summary:</div>
                  <p className="text-[#57534E] leading-relaxed">
                    {selectedApproval.reason}
                  </p>
                  <p className="text-[#78716C] text-[11px]">
                    Customer delivered product within valid 14-day return window. No prior refund issued. Policy requires manual human authorization before SQLite refund execution.
                  </p>
                </div>

                {/* Supervisor Notes */}
                {(selectedApproval.status || 'pending') === 'pending' ? (
                  <div>
                    <label className="text-[11px] font-semibold text-[#1C1917] mb-1 block">
                      Supervisor Approval Notes (Audit Logged):
                    </label>
                    <input
                      type="text"
                      value={decisionNotes}
                      onChange={(e) => setDecisionNotes(e.target.value)}
                      placeholder="e.g. Approved after verifying invoice with customer"
                      className="w-full bg-white border border-[#D6D3D1] rounded-lg p-2.5 text-xs text-[#1C1917] focus:outline-none focus:border-[#C2410C]"
                    />
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-white border border-[#D6D3D1] space-y-1 text-[11px]">
                    <span className="font-semibold text-[#1C1917] block">Logged Supervisor Decision:</span>
                    <p
                      className={
                        selectedApproval.status === 'approved'
                          ? 'text-[#16A34A] font-semibold'
                          : 'text-[#DC2626] font-semibold'
                      }
                    >
                      Status: {selectedApproval.status?.toUpperCase()}
                    </p>
                    {selectedApproval.decision_notes && (
                      <p className="text-[#57534E]">Notes: {selectedApproval.decision_notes}</p>
                    )}
                    {selectedApproval.supervisor_id && (
                      <p className="text-[#78716C] font-mono">
                        By: {selectedApproval.supervisor_id}{' '}
                        {selectedApproval.decided_at &&
                          `• ${new Date(selectedApproval.decided_at).toLocaleString()}`}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-6 pt-4 border-t border-[#D6D3D1] flex items-center justify-end space-x-3">
                {(selectedApproval.status || 'pending') === 'pending' ? (
                  <>
                    <button
                      disabled={actionLoading}
                      onClick={() => handleDecision(selectedApproval, 'rejected', decisionNotes)}
                      className="px-4 py-2 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                    >
                      <XCircle className="w-4 h-4" />
                      Decline Request
                    </button>

                    <button
                      disabled={actionLoading}
                      onClick={() => handleDecision(selectedApproval, 'approved', decisionNotes)}
                      className="px-5 py-2 rounded-lg bg-[#16A34A] hover:bg-[#15803D] text-white font-semibold text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      Authorize & Approve {selectedApproval.amount > 0 ? `(Rs ${selectedApproval.amount.toFixed(2)})` : ''}
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setSelectedApproval(null)}
                    className="px-5 py-2 rounded-lg bg-white hover:bg-[#E7E5E4] text-[#1C1917] font-semibold text-xs transition-all cursor-pointer border border-[#D6D3D1]"
                  >
                    Close Dossier
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
