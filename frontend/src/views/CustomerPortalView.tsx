import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Bot,
  AlertCircle,
  RefreshCw,
  Clock,
  ChevronRight
} from 'lucide-react';
import {
  UserProfile,
  TraceStep,
  WhyDecision,
  sendChatTurn,
  subscribeChatStream
} from '../api/client';
import { LiveAgentFlow } from '../components/LiveAgentFlow';
import { EvidenceCard } from '../components/EvidenceCard';
import { WhyDecisionCard } from '../components/WhyDecisionCard';
import { DemoScenarioChips } from '../components/DemoScenarioChips';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  responseTimeMs?: number;
  action?: 'answer' | 'clarify' | 'reject' | 'escalate' | 'hitl_interrupt';
  language?: string;
  sentiment?: 'positive' | 'neutral' | 'frustrated' | 'abusive';
  priority?: 'Low' | 'Medium' | 'High' | 'Critical';
  grounded?: boolean | null;
  citations?: any[];
  whyDecision?: WhyDecision;
  isPendingApproval?: boolean;
}

interface CustomerPortalViewProps {
  currentUser: UserProfile | null;
  onNavigateToSupervisor: () => void;
}

export const CustomerPortalView: React.FC<CustomerPortalViewProps> = ({
  currentUser,
  onNavigateToSupervisor
}) => {
  const [threadId, setThreadId] = useState<string>(() => `thread_${Math.random().toString(36).substring(2, 9)}`);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome_1',
      sender: 'assistant',
      content: 'Namaste! Welcome to SentinelCX. How can I assist you with your orders, refunds, billing, or account today?',
      timestamp: '10:00 AM',
      action: 'answer',
      language: 'en',
      sentiment: 'neutral',
      priority: 'Low',
      grounded: true
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Live Agent Flow State
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
  const [currentTrace, setCurrentTrace] = useState<TraceStep[]>([]);
  const [currentWhyDecision, setCurrentWhyDecision] = useState<WhyDecision | undefined>(undefined);
  const [isCurrentPendingApproval, setIsCurrentPendingApproval] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamCleanupRef = useRef<(() => void) | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  useEffect(() => {
    return () => {
      streamCleanupRef.current?.();
    };
  }, []);

  const handleSendMessage = async (textToSend?: string, targetThreadId?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isProcessing) return;
    const activeThread = targetThreadId || threadId;
    const requestStartedAt = performance.now();

    // Append User Message
    const userMsg: Message = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsProcessing(true);

    // Reset Live Flow Visualizer for the new turn
    setActiveNode('pii');
    setCompletedNodes(new Set());
    setCurrentTrace([]);
    setCurrentWhyDecision(undefined);
    setIsCurrentPendingApproval(false);

    try {
      streamCleanupRef.current?.();
      let eventCount = 0;

      // Stream Live Agent Events via SSE for real-time visualization
      const unsubscribe = subscribeChatStream(
        activeThread,
        query,
        currentUser?.user_id || 'user_1',
        (eventType, data) => {
          eventCount++;

          if (eventType === 'node_start') {
            setActiveNode(data.node);
          } else if (eventType === 'node_complete') {
            setActiveNode(null);
            setCompletedNodes((prev) => new Set([...prev, data.node]));
            setCurrentTrace((prev) => [...prev, {
              node: data.node,
              summary: data.summary,
              duration_ms: data.duration_ms,
              timestamp: data.timestamp,
            }]);
          } else if (eventType === 'interrupt') {
            setActiveNode('hitl_interrupt');
          } else if (eventType === 'complete') {
            setIsProcessing(false);
            setActiveNode(null);
            setCurrentTrace(data.trace || []);
            setCompletedNodes((prev) => new Set([
              ...prev,
              ...(data.trace || []).map((step: TraceStep) => step.node),
              ...(data.action === 'hitl_interrupt' ? ['hitl_interrupt'] : []),
            ]));

            const why: WhyDecision | undefined = data.why_decision;
            setCurrentWhyDecision(why);
            setIsCurrentPendingApproval(Boolean(data.is_pending_approval));

            const botMsg: Message = {
              id: `bot_${Date.now()}`,
              sender: 'assistant',
              content: data.answer || 'No response generated.',
              responseTimeMs: performance.now() - requestStartedAt,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              action: data.action,
              language: data.language,
              sentiment: data.sentiment,
              priority: data.priority,
              grounded: data.grounded,
              citations: data.citations,
              whyDecision: why,
              isPendingApproval: data.is_pending_approval
            };
            setMessages((prev) => [...prev, botMsg]);
          } else if (eventType === 'error') {
            setIsProcessing(false);
            setActiveNode(null);
            setMessages((prev) => [
              ...prev,
              {
                id: `err_${Date.now()}`,
                sender: 'assistant',
                content: `An error occurred: ${data.error || 'Agent execution failed'}`,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                action: 'clarify'
              }
            ]);
          }
        },
        async (streamErr) => {
          // Fallback to synchronous REST endpoint if SSE stream fails or is closed
          if (eventCount === 0) {
            try {
              const res = await sendChatTurn(activeThread, query, currentUser?.user_id || 'user_1');
              setCurrentWhyDecision(res.why_decision);
              setIsCurrentPendingApproval(Boolean(res.is_pending_approval));
              setCurrentTrace(res.trace);
              setCompletedNodes(new Set(res.trace.map((step) => step.node)));

              const botMsg: Message = {
                id: `bot_${Date.now()}`,
                sender: 'assistant',
                content: res.answer,
                responseTimeMs: performance.now() - requestStartedAt,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                action: res.action as any,
                language: res.language,
                sentiment: res.sentiment as any,
                priority: res.priority as any,
                grounded: res.grounded,
                citations: res.citations,
                whyDecision: res.why_decision,
                isPendingApproval: res.is_pending_approval
              };
              setMessages((prev) => [...prev, botMsg]);
            } catch (restErr: any) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `err_${Date.now()}`,
                  sender: 'assistant',
                  content: `System notification: ${restErr.message || 'Service temporarily unavailable'}`,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  action: 'clarify'
                }
              ]);
            } finally {
              setIsProcessing(false);
              setActiveNode(null);
            }
          } else {
            console.warn('SSE stream interrupted midway:', streamErr);
            setIsProcessing(false);
            setActiveNode(null);
            setMessages((prev) => [...prev, {
              id: `err_${Date.now()}`,
              sender: 'assistant',
              content: 'The connection was interrupted before a response arrived. Check the Command Center for the request status before retrying.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              action: 'clarify',
            }]);
          }
        }
      );
      streamCleanupRef.current = unsubscribe;
    } catch (e: any) {
      console.error('Chat turn initiation error:', e);
      setIsProcessing(false);
      setActiveNode(null);
      setMessages((prev) => [...prev, {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        content: `System notification: ${e.message || 'Unable to start chat request'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        action: 'clarify',
      }]);
    }
  };

  const handleSelectScenario = (scenario: any) => {
    const newThread = `thread_${Math.random().toString(36).substring(2, 9)}`;
    setThreadId(newThread);
    setInputQuery(scenario.query);
    handleSendMessage(scenario.query, newThread);
  };

  const handleNewSession = () => {
    streamCleanupRef.current?.();
    streamCleanupRef.current = null;
    setIsProcessing(false);
    setActiveNode(null);
    const newThread = `thread_${Math.random().toString(36).substring(2, 9)}`;
    setThreadId(newThread);
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        sender: 'assistant',
        content: `New session started (${newThread}). How may I assist you today?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        action: 'answer',
        grounded: true
      }
    ]);
    setCompletedNodes(new Set());
    setCurrentTrace([]);
    setCurrentWhyDecision(undefined);
    setIsCurrentPendingApproval(false);
  };

  return (
    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-100px)] min-h-[680px]">
      {/* LEFT / CENTER: Customer Portal Chat (7 cols) */}
      <div className="lg:col-span-7 flex flex-col h-full bg-[#F5F5F4] rounded-xl border border-[#D6D3D1] overflow-hidden shadow-xs">
        {/* Chat Header */}
        <div className="p-4 border-b border-[#D6D3D1] bg-[#E7E5E4]/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-[#C2410C] flex items-center justify-center text-white shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-[#1C1917] font-display">SentinelCX Support</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E7E5E4] border border-[#D6D3D1] text-[#16A34A] font-semibold flex items-center gap-1 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#16A34A] animate-pulse" />
                  Active
                </span>
              </div>
              <p className="text-[11px] text-[#57534E]">
                User: <span className="text-[#1C1917] font-semibold">{currentUser?.name || 'Ananya'}</span> ({currentUser?.email})
                {currentUser?.is_verified ? (
                  <span className="ml-1 text-[#16A34A] font-semibold text-[10px]">✓ Verified</span>
                ) : (
                  <span className="ml-1 text-[#D97706] font-semibold text-[10px]">⚠ Unverified</span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleNewSession}
              title="Start a fresh conversation thread"
              className="px-3 py-1.5 rounded-lg bg-[#F5F5F4] hover:bg-[#E7E5E4] text-[#57534E] hover:text-[#1C1917] transition-all border border-[#D6D3D1] text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5 text-[#C2410C]" />
              <span className="hidden sm:inline">New Thread</span>
            </button>
          </div>
        </div>

        {/* Demo Scenario Chips */}
        <div className="px-4 border-b border-[#D6D3D1] bg-[#F5F5F4]">
          <DemoScenarioChips onSelectScenario={handleSelectScenario} disabled={isProcessing} />
        </div>

        {/* Message Thread Scroll Area */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#FAFAF9]">
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                {/* Bubble */}
                <div
                  className={`max-w-[85%] rounded-xl p-4 text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-[#C2410C] text-white rounded-tr-none shadow-sm'
                      : 'bg-[#FFFFFF] text-[#1C1917] border border-[#D6D3D1] rounded-tl-none shadow-xs'
                  }`}
                >
                  {/* Assistant Header Badges */}
                  {msg.sender === 'assistant' && (
                    <div className="flex flex-wrap items-center gap-1.5 mb-2 pb-2 border-b border-[#D6D3D1] text-[10px]">
                      {msg.language && (
                        <span className="px-2 py-0.5 rounded-full bg-[#E7E5E4] text-[#57534E] font-mono uppercase font-semibold">
                          {msg.language}
                        </span>
                      )}
                      {msg.priority && (
                        <span
                          className={`px-2 py-0.5 rounded-full font-semibold ${
                            msg.priority === 'Critical'
                              ? 'bg-[#DC2626]/10 text-[#DC2626] border border-[#DC2626]/30'
                              : msg.priority === 'High'
                              ? 'bg-[#D97706]/10 text-[#D97706] border border-[#D97706]/30'
                              : 'bg-[#E7E5E4] text-[#57534E]'
                          }`}
                        >
                          {msg.priority} Priority
                        </span>
                      )}
                      {msg.sentiment && msg.sentiment !== 'neutral' && (
                        <span
                          className={`px-2 py-0.5 rounded-full font-semibold ${
                            msg.sentiment === 'abusive'
                              ? 'bg-[#DC2626]/10 text-[#DC2626]'
                              : 'bg-[#D97706]/10 text-[#D97706]'
                          }`}
                        >
                          {msg.sentiment}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Message Body Text */}
                  <div className="whitespace-pre-wrap font-normal text-[13px] leading-relaxed">
                    {msg.content}
                  </div>

                  {/* Pending Approval Amber Notice */}
                  {msg.isPendingApproval && (
                    <div className="mt-3 p-3.5 rounded-lg bg-[#FFFBEB] border border-[#F59E0B] text-[#92400E]">
                      <div className="flex items-center space-x-2 font-bold text-xs mb-1">
                        <AlertCircle className="w-4 h-4 text-[#F59E0B] animate-pulse" />
                        <span>APPROVAL GATE ACTIVATED (&gt; Rs 2,000)</span>
                      </div>
                      <p className="text-[11px] text-[#B45309] leading-relaxed">
                        This high-value transaction has paused execution at the Human-in-the-Loop policy gate. You can inspect the full handoff dossier and approve or decline in the Supervisor Command Center.
                      </p>
                      <button
                        onClick={onNavigateToSupervisor}
                        className="mt-2.5 px-3 py-1.5 rounded-lg bg-[#C2410C] hover:bg-[#9A3412] text-white font-semibold text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                      >
                        Open Approval Queue in Command Center <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Grounded Evidence Card */}
                  {msg.sender === 'assistant' && msg.citations && msg.citations.length > 0 && (
                    <EvidenceCard grounded={msg.grounded} citations={msg.citations} />
                  )}

                  {/* Why this decision Explainability Card */}
                  {msg.sender === 'assistant' && msg.whyDecision && (
                    <WhyDecisionCard whyDecision={msg.whyDecision} />
                  )}
                </div>

                {/* Timestamp and measured request-to-response duration */}
                <div className="text-[10px] text-[#78716C] mt-1 px-1 font-mono flex items-center gap-3">
                  <span>{msg.timestamp}</span>
                  {msg.responseTimeMs !== undefined && (
                    <span className="inline-flex items-center gap-1" title="Elapsed time from sending the request to receiving the complete reply, including network time">
                      <Clock className="w-3 h-3" />
                      Response time: {msg.responseTimeMs < 1000
                        ? `${Math.round(msg.responseTimeMs)} ms`
                        : `${(msg.responseTimeMs / 1000).toFixed(2)} s`}
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center space-x-2 text-[#78716C] text-xs py-2"
            >
              <div className="w-2 h-2 rounded-full bg-[#C2410C] animate-ping" />
              <span>Multi-agent reasoning in progress ({activeNode || 'evaluating'})...</span>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-[#D6D3D1] bg-[#E7E5E4]/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask anything in English or Hinglish (e.g. 'ORD-1001 ka refund chahiye', 'policy window', etc.)..."
              disabled={isProcessing}
              className="flex-1 bg-white border border-[#D6D3D1] focus:border-[#C2410C] rounded-lg px-4 py-2.5 text-xs text-[#1C1917] placeholder-[#78716C] focus:outline-none transition-all shadow-xs"
            />
            <button
              type="submit"
              disabled={isProcessing || !inputQuery.trim()}
              className="px-4 py-2.5 rounded-lg bg-[#C2410C] hover:bg-[#9A3412] disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-xs hover:shadow-md"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT: Live Agent Flow Signature Feature (5 cols) */}
      <div className="lg:col-span-5 flex flex-col h-full">
        <LiveAgentFlow
          activeNode={activeNode}
          completedNodes={completedNodes}
          trace={currentTrace}
          whyDecision={currentWhyDecision}
          isPendingApproval={isCurrentPendingApproval}
        />
      </div>
    </div>
  );
};
