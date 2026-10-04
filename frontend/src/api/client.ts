export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  is_verified: boolean;
  role: string;
  orders: Array<{
    order_id: string;
    item_name: string;
    amount: number;
    currency: string;
    status: string;
    purchase_date: string;
    delivery_date?: string;
  }>;
}

export interface Citation {
  source: string;
  title: string;
  category: string;
  score: number;
  snippet: string;
}

export interface TraceStep {
  node: string;
  summary: string;
  duration_ms: number;
  timestamp?: string;
}

export interface WhyDecision {
  intent?: string;
  confidence?: number;
  policy_rule?: string;
  final_route?: string;
  reason?: string;
}

export interface ChatResponse {
  thread_id: string;
  user_query: string;
  answer: string;
  action: 'answer' | 'clarify' | 'reject' | 'escalate' | 'hitl_interrupt';
  intent: string;
  intent_confidence: number;
  sentiment: 'positive' | 'neutral' | 'frustrated' | 'abusive';
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  language: string;
  is_transactional: boolean;
  extracted_order_id?: string;
  amount_at_risk?: number;
  sla_deadline?: string;
  grounded?: boolean | null;
  citations: Citation[];
  why_decision: WhyDecision;
  trace: TraceStep[];
  is_pending_approval: boolean;
  pending_approval_id?: string;
  handoff_dossier?: any;
  pii_counts: Record<string, number>;
}

export interface Ticket {
  ticket_id: string;
  thread_id: string;
  user_id: string;
  user_name: string;
  query: string;
  action: string;
  intent: string;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  sentiment: 'positive' | 'neutral' | 'frustrated' | 'abusive';
  status: 'open' | 'pending_approval' | 'resolved' | 'escalated' | 'rejected';
  sla_deadline?: string;
  created_at: string;
  updated_at: string;
  amount_at_risk: number;
}

export interface PendingApproval {
  approval_id: string;
  thread_id: string;
  order_id?: string;
  amount: number;
  user_id: string;
  reason: string;
  dossier: any;
  why_decision: WhyDecision;
  created_at: string;
}

export interface MetricsSummary {
  timestamp: string;
  routing_accuracy_pct: number;
  grounding_failure_rate_pct: number;
  policy_violations: number;
  pii_leak_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  scoreboard_status: string;
  active_ticket_count: number;
  auto_resolved_count: number;
  escalated_count: number;
  pending_approval_count: number;
  priority_distribution: Record<string, number>;
}

export interface AuditRecord {
  id?: number;
  log_id?: number;
  timestamp: string;
  session: string;
  action: string;
  input: string;
  decision: string;
  reason: string;
}

export interface PiiFeedItem {
  id: string;
  type: string;
  count: number;
  masked_token: string;
  timestamp: string;
  channel: string;
  thread_id?: string;
}

export interface RedteamAttackResult {
  attack: string;
  input: string;
  blocked_by: string;
  outcome: string;
  passed: boolean;
  trace: Array<{
    node: string;
    summary: string;
    duration_ms: number;
  }>;
}

export interface RedteamReport {
  timestamp: string;
  total_attacks: number;
  passed_count: number;
  failed_count: number;
  safety_rate_pct: number;
  all_passed: boolean;
  results: RedteamAttackResult[];
}

// ============================================================================
// API Client Functions
// ============================================================================

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}

export async function fetchDemoUsers(): Promise<UserProfile[]> {
  const res = await fetch(`${API_BASE_URL}/demo/users`);
  if (!res.ok) throw new Error('Failed to fetch demo users');
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsSummary> {
  const res = await fetch(`${API_BASE_URL}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch system metrics');
  return res.json();
}

export async function fetchScoreboard(force: boolean = false): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/scoreboard?force=${force}`);
  if (!res.ok) throw new Error('Failed to fetch evaluation scoreboard');
  return res.json();
}

export async function fetchTickets(status?: string, priority?: string): Promise<Ticket[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (priority) params.append('priority', priority);
  const res = await fetch(`${API_BASE_URL}/tickets?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch tickets');
  return res.json();
}

export async function fetchApprovals(): Promise<PendingApproval[]> {
  const res = await fetch(`${API_BASE_URL}/approvals`);
  if (!res.ok) throw new Error('Failed to fetch pending approvals');
  return res.json();
}

export async function postApprovalDecision(
  threadId: string,
  decision: 'approved' | 'rejected',
  supervisorId: string = 'sup_vikram_204',
  notes?: string
): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/approvals/${threadId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, supervisor_id: supervisorId, notes }),
  });
  if (!res.ok) throw new Error('Failed to submit approval decision');
  return res.json();
}

export async function fetchAuditLogs(action?: string, limit: number = 50): Promise<AuditRecord[]> {
  const params = new URLSearchParams();
  if (action) params.append('action', action);
  params.append('limit', limit.toString());
  const res = await fetch(`${API_BASE_URL}/audit?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch audit log');
  return res.json();
}

export async function fetchPiiFeed(limit: number = 25): Promise<PiiFeedItem[]> {
  const res = await fetch(`${API_BASE_URL}/pii-feed?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch PII audit feed');
  return res.json();
}

export async function fetchRedteamReport(): Promise<RedteamReport> {
  const res = await fetch(`${API_BASE_URL}/redteam`);
  if (!res.ok) throw new Error('Failed to fetch redteam report');
  return res.json();
}

export async function runRedteamSuite(): Promise<RedteamReport> {
  const res = await fetch(`${API_BASE_URL}/redteam/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to execute red-team suite');
  return res.json();
}

export async function resetDemoState(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/demo/reset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reset demo state');
  return res.json();
}

export async function sendChatTurn(
  threadId: string,
  query: string,
  userId: string = 'user_1'
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, user_query: query, user_id: userId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Chat request failed');
  }
  return res.json();
}

export function subscribeChatStream(
  threadId: string,
  query: string,
  userId: string = 'user_1',
  onEvent: (eventType: string, data: any) => void,
  onError?: (err: any) => void
): () => void {
  const params = new URLSearchParams({
    thread_id: threadId,
    user_query: query,
    user_id: userId,
  });

  const eventSource = new EventSource(`${API_BASE_URL}/chat/stream?${params.toString()}`);

  eventSource.addEventListener('start', (e: MessageEvent) => {
    try { onEvent('start', JSON.parse(e.data)); } catch {}
  });

  eventSource.addEventListener('node_complete', (e: MessageEvent) => {
    try { onEvent('node_complete', JSON.parse(e.data)); } catch {}
  });

  eventSource.addEventListener('interrupt', (e: MessageEvent) => {
    try { onEvent('interrupt', JSON.parse(e.data)); } catch {}
  });

  eventSource.addEventListener('complete', (e: MessageEvent) => {
    try {
      onEvent('complete', JSON.parse(e.data));
    } catch {}
    eventSource.close();
  });

  eventSource.addEventListener('error', (e: any) => {
    if (onError) onError(e);
    eventSource.close();
  });

  return () => {
    eventSource.close();
  };
}
