import React from 'react';
import {
  Shield,
  Activity,
  Layers,
  RotateCcw,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  User,
  Users
} from 'lucide-react';
import { UserProfile } from '../api/client';

interface NavbarProps {
  currentTab: 'landing' | 'portal' | 'supervisor' | 'safety';
  setCurrentTab: (tab: 'landing' | 'portal' | 'supervisor' | 'safety') => void;
  users: UserProfile[];
  selectedUser: UserProfile | null;
  onSelectUser: (user: UserProfile) => void;
  pendingApprovalsCount: number;
  onResetDemo: () => void;
  isResetting: boolean;
  backendOnline: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  users,
  selectedUser,
  onSelectUser,
  pendingApprovalsCount,
  onResetDemo,
  isResetting,
  backendOnline,
}) => {
  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-6 py-3.5 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand / Logo */}
        <div
          className="flex items-center space-x-3 cursor-pointer group"
          onClick={() => setCurrentTab('landing')}
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-sky-500/20 group-hover:scale-105 transition-transform">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-base tracking-tight text-white group-hover:text-sky-400 transition-colors">
                SENTINEL<span className="text-sky-400 font-extrabold">CX</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-950 border border-sky-800/60 text-sky-300 font-mono">
                v2.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">LLMs reason, Python governs</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1.5 p-1 rounded-xl bg-slate-900/80 border border-slate-800">
          <button
            onClick={() => setCurrentTab('landing')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentTab === 'landing'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Overview
          </button>

          <button
            onClick={() => setCurrentTab('portal')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentTab === 'portal'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Customer Portal & Live Flow
          </button>

          <button
            onClick={() => setCurrentTab('supervisor')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 relative ${
              currentTab === 'supervisor'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Command Center
            {pendingApprovalsCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-amber-500 text-black font-extrabold text-[9px] flex items-center justify-center animate-bounce">
                {pendingApprovalsCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setCurrentTab('safety')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentTab === 'safety'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            Safety Proof (Red-Team)
          </button>
        </nav>

        {/* Right Tools: User Switcher, Reset Demo, Backend Status */}
        <div className="flex items-center space-x-3">
          {/* Demo User Switcher Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800 text-xs">
            <User className="w-3.5 h-3.5 text-sky-400" />
            <select
              aria-label="Select demo user profile"
              className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none cursor-pointer"
              value={selectedUser?.user_id || 'user_1'}
              onChange={(e) => {
                const found = users.find((u) => u.user_id === e.target.value);
                if (found) onSelectUser(found);
              }}
            >
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id} className="bg-slate-900 text-slate-200">
                  {u.name} ({u.is_verified ? 'Verified' : 'Unverified'})
                </option>
              ))}
            </select>
          </div>

          {/* Reset Demo Button */}
          <button
            onClick={onResetDemo}
            disabled={isResetting}
            title="Reset SQLite database to fresh clean seed"
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-all border border-slate-700/60 active:scale-95 flex items-center gap-1.5 text-xs font-medium disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin text-sky-400' : ''}`} />
            <span>Reset Demo</span>
          </button>

          {/* Live Backend Connection Indicator */}
          <div className="flex items-center space-x-1.5 pl-2 border-l border-slate-800">
            <div
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="text-[11px] font-mono text-slate-400">
              {backendOnline ? 'API 8000' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
