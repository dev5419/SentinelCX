import React from 'react';
import {
  Shield,
  Activity,
  Layers,
  RotateCcw,
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
    <header className="sticky top-0 z-50 bg-[#F5F5F4]/95 border-b border-[#D6D3D1] px-6 py-3 backdrop-blur-md shadow-sm">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand / Logo */}
        <div
          className="flex items-center space-x-3 cursor-pointer group"
          onClick={() => setCurrentTab('landing')}
        >
          <img
            src="/Logo.png"
            alt="SentinelCX logo"
            className="w-10 h-10 object-contain shrink-0"
            width={40}
            height={40}
          />
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-base tracking-tight text-[#1C1917] group-hover:text-[#C2410C] transition-colors font-display">
                SENTINEL<span className="text-[#C2410C] font-extrabold">CX</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E7E5E4] border border-[#D6D3D1] text-[#57534E] font-mono font-medium">
                v2.0
              </span>
            </div>
            <p className="text-[11px] text-[#57534E] font-medium">LLMs reason, Python governs</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 p-1 rounded-xl bg-[#E7E5E4]/90 border border-[#D6D3D1]">
          <button
            onClick={() => setCurrentTab('landing')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              currentTab === 'landing'
                ? 'bg-[#C2410C] text-white shadow-sm'
                : 'text-[#57534E] hover:text-[#1C1917] hover:bg-[#F5F5F4]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Overview
          </button>

          <button
            onClick={() => setCurrentTab('portal')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              currentTab === 'portal'
                ? 'bg-[#C2410C] text-white shadow-sm'
                : 'text-[#57534E] hover:text-[#1C1917] hover:bg-[#F5F5F4]'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Customer Portal & Live Flow
          </button>

          <button
            onClick={() => setCurrentTab('supervisor')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 relative cursor-pointer ${
              currentTab === 'supervisor'
                ? 'bg-[#C2410C] text-white shadow-sm'
                : 'text-[#57534E] hover:text-[#1C1917] hover:bg-[#F5F5F4]'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Command Center
            {pendingApprovalsCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-[#F59E0B] text-[#1C1917] font-bold text-[9px] flex items-center justify-center animate-bounce shadow-sm">
                {pendingApprovalsCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setCurrentTab('safety')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              currentTab === 'safety'
                ? 'bg-[#C2410C] text-white shadow-sm'
                : 'text-[#57534E] hover:text-[#1C1917] hover:bg-[#F5F5F4]'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            Safety Proof (Red-Team)
          </button>
        </nav>

        {/* Right Tools: User Switcher, Reset Demo, Backend Status */}
        <div className="flex items-center space-x-3">
          {/* Demo User Switcher Dropdown */}
          <div className="flex items-center space-x-2 bg-[#F5F5F4] px-3 py-1.5 rounded-lg border border-[#D6D3D1] text-xs shadow-xs">
            <User className="w-3.5 h-3.5 text-[#C2410C]" />
            <select
              aria-label="Select demo user profile"
              className="bg-transparent text-[#1C1917] text-xs font-medium focus:outline-none cursor-pointer"
              value={selectedUser?.user_id || 'user_1'}
              onChange={(e) => {
                const found = users.find((u) => u.user_id === e.target.value);
                if (found) onSelectUser(found);
              }}
            >
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id} className="bg-[#F5F5F4] text-[#1C1917]">
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
            className="px-3 py-1.5 rounded-lg bg-[#F5F5F4] hover:bg-[#E7E5E4] text-[#57534E] hover:text-[#1C1917] transition-all border border-[#D6D3D1] active:scale-95 flex items-center gap-1.5 text-xs font-semibold disabled:opacity-50 cursor-pointer shadow-xs"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin text-[#C2410C]' : 'text-[#57534E]'}`} />
            <span>Reset Demo</span>
          </button>

          {/* Live Backend Connection Indicator */}
          <div className="flex items-center space-x-1.5 pl-2 border-l border-[#D6D3D1]">
            <div
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-[#16A34A] shadow-[0_0_6px_rgba(22,163,74,0.5)] animate-pulse' : 'bg-[#DC2626]'
              }`}
            />
            <span className="text-[11px] font-mono text-[#57534E] font-medium">
              {backendOnline ? 'API 8000' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
