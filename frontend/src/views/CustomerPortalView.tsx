import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  User,
  Shield,
  Bot,
  AlertCircle,
  Clock,
  Sparkles,
  RefreshCw,
  CheckCircle,
  ExternalLink,
  ChevronRight,
  Package
} from 'lucide-react';
import {
  UserProfile,
  ChatResponse,
  TraceStep,
  WhyDecision,
  sendChatTurn,
  subscribeChatStream
} from '../api/client';
import { LiveAgentFlow } from '../components/LiveAgentFlow';
import { EvidenceCard } from '../components/EvidenceCard';
import { WhyDecisionCard } from '../components/WhyDecisionCard';
import { DemoScenarioChips, DEMO_SCENARIOS } from '../components/DemoScenarioChips';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
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
      content: 'Namaste! Welcome to Enterprise Support. How can I assist you with your orders, refunds, billing, or account today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  const handleSendMessage = async (textToSend?: string, targetThreadId?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isProcessing) return;
    const activeThread = targetThreadId || threadId;

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
      // Stream Live Agent Events via SSE for real-time visualization
      const unsubscribe = subscribeChatStream(
        activeThread,
        query,
        currentUser?.user_id || 'user_1',
        (eventType, data) => {
          if (eventType === 'node_complete') {
            setActiveNode(null);
            setCompletedNodes((prev) => new Set([...prev, data.node]));
            if (data.summary) {
              setCurrentTrace((prev) => [
                ...prev,
                { node: data.node, summary: data.summary, duration_ms: data.duration_ms }
              ]);
            }
          } else if (eventType === 'interrupt') {
            setIsCurrentPendingApproval(true);
          } else if (eventType === 'complete') {
            // Process complete payload
            setCurrentWhyDecision(data.why_decision);
            const isInt = data.action === 'hitl_interrupt' || data.is_pending_approval;
            setIsCurrentPendingApproval(isInt);

            const botMsg: Message = {
              id: `bot_${Date.now()}`,
              sender: 'assistant',
              content: data.answer || 'Your request has been processed.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              action: data.action,
              language: data.language,
              sentiment: data.sentiment,
              priority: data.priority,
              grounded: data.grounded,
              citations: data.citations || [],
              whyDecision: data.why_decision,
              isPendingApproval: isInt
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsProcessing(false);
          }
        },
        async (_err) => {
          // Fallback to standard REST if SSE connection drops
          try {
            const res = await sendChatTurn(activeThread, query, currentUser?.user_id || 'user_1');
            setCompletedNodes(new Set(res.trace.map((t) => t.node)));
            setCurrentTrace(res.trace);
            setCurrentWhyDecision(res.why_decision);
            setIsCurrentPendingApproval(res.is_pending_approval);

            const botMsg: Message = {
              id: `bot_${Date.now()}`,
              sender: 'assistant',
              content: res.answer,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              action: res.action,
              language: res.language,
              sentiment: res.sentiment,
              priority: res.priority,
              grounded: res.grounded,
              citations: res.citations || [],
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
        }
      );
    } catch (e: any) {
      setIsProcessing(false);
    }
  };

  const handleSelectScenario = (scenario: any) => {
    const newThread = `thread_${Math.random().toString(36).substring(2, 9)}`;
    setThreadId(newThread);
    setInputQuery(scenario.query);
    handleSendMessage(scenario.query, newThread);
  };

  const handleNewSession = () => {
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
      <div className="lg:col-span-7 flex flex-col h-full glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
        {/* Chat Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-white">Enterprise AI Support</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Active
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                User: <span className="text-slate-200 font-medium">{currentUser?.name || 'Ananya'}</span> ({currentUser?.email})
                {currentUser?.is_verified ? (
                  <span className="ml-1 text-emerald-400 font-semibold text-[10px]">✓ Verified</span>
                ) : (
                  <span className="ml-1 text-amber-400 font-semibold text-[10px]">⚠ Unverified</span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleNewSession}
              title="Start a fresh conversation thread"
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-all border border-slate-700 text-xs flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Thread</span>
            </button>
          </div>
        </div>

        {/* Demo Scenario Chips */}
        <div className="px-4 border-b border-slate-800/60 bg-slate-950/40">
          <DemoScenarioChips onSelectScenario={handleSelectScenario} disabled={isProcessing} />
        </div>

        {/* Message Thread Scroll Area */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
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
                  className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white rounded-tr-none shadow-md shadow-sky-500/10'
                      : 'bg-slate-900/90 text-slate-200 border border-slate-800/90 rounded-tl-none shadow-md'
                  }`}
                >
                  {/* Assistant Header Badges */}
                  {msg.sender === 'assistant' && (
                    <div className="flex flex-wrap items-center gap-1.5 mb-2 pb-2 border-b border-slate-800/80 text-[10px]">
                      {msg.language && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono uppercase">
                          {msg.language}
                        </span>
                      )}
                      {msg.priority && (
                        <span
                          className={`px-1.5 py-0.5 rounded font-medium ${
                            msg.priority === 'Critical'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : msg.priority === 'High'
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {msg.priority} Priority
                        </span>
                      )}
                      {msg.sentiment && msg.sentiment !== 'neutral' && (
                        <span
                          className={`px-1.5 py-0.5 rounded font-medium ${
                            msg.sentiment === 'abusive'
                              ? 'bg-rose-950 text-rose-300'
                              : 'bg-amber-950 text-amber-300'
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
                    <div className="mt-3 p-3 rounded-xl bg-amber-950/60 border border-amber-600/70 text-amber-200">
                      <div className="flex items-center space-x-2 font-bold text-xs mb-1">
                        <AlertCircle className="w-4 h-4 text-amber-400 animate-pulse" />
                        <span>APPROVAL GATE ACTIVATED (&gt; Rs 2,000)</span>
                      </div>
                      <p className="text-[11px] text-amber-300/90 leading-relaxed">
                        This high-value transaction has paused execution at the Human-in-the-Loop policy gate. You can inspect the full handoff dossier and approve or decline in the Supervisor Command Center.
                      </p>
                      <button
                        onClick={onNavigateToSupervisor}
                        className="mt-2.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
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

                {/* Timestamp */}
                <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center space-x-2 text-slate-400 text-xs py-2"
            >
              <div className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
              <span>Multi-agent reasoning in progress ({activeNode || 'evaluating'})...</span>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/70">
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
              className="flex-1 bg-slate-950/80 border border-slate-700/80 focus:border-sky-500 rounded-xl px-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
            />
            <button
              type="submit"
              disabled={isProcessing || !inputQuery.trim()}
              className="px-4 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer"
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
