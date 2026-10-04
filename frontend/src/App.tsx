import React, { useState, useEffect, useCallback } from 'react';
import {
  UserProfile,
  MetricsSummary,
  fetchHealth,
  fetchDemoUsers,
  fetchMetrics,
  fetchApprovals,
  resetDemoState
} from './api/client';
import { Navbar } from './components/Navbar';
import { LandingView } from './views/LandingView';
import { CustomerPortalView } from './views/CustomerPortalView';
import { SupervisorCommandCenterView } from './views/SupervisorCommandCenterView';
import { SafetyProofView } from './views/SafetyProofView';

export function App() {
  const [currentTab, setCurrentTab] = useState<'landing' | 'portal' | 'supervisor' | 'safety'>('landing');
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  const refreshSystemData = useCallback(async () => {
    try {
      const health = await fetchHealth();
      setBackendOnline(health.status === 'ok');

      const [usersData, metricsData, approvalsData] = await Promise.all([
        fetchDemoUsers(),
        fetchMetrics(),
        fetchApprovals()
      ]);

      setUsers(usersData);
      setSelectedUser((prev) => prev || (usersData.length > 0 ? usersData[0] : null));
      setMetrics(metricsData);
      setPendingApprovalsCount(approvalsData.length);
    } catch (e) {
      console.warn('Backend connection unavailable:', e);
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    refreshSystemData();
    const interval = setInterval(refreshSystemData, 6000);
    return () => clearInterval(interval);
  }, [refreshSystemData]);

  const handleResetDemo = async () => {
    setIsResetting(true);
    try {
      await resetDemoState();
      await refreshSystemData();
      alert('Demo state reset successfully: SQLite restored to clean seed, memory checkpointer cleared.');
    } catch (e: any) {
      alert(`Reset failed: ${e.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col bg-grid-pattern selection:bg-sky-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        users={users}
        selectedUser={selectedUser}
        onSelectUser={setSelectedUser}
        pendingApprovalsCount={pendingApprovalsCount}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
        backendOnline={backendOnline}
      />

      {/* Main Content View */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        {currentTab === 'landing' && (
          <LandingView
            metrics={metrics}
            onLaunchDemo={() => setCurrentTab('portal')}
            onOpenCommandCenter={() => setCurrentTab('supervisor')}
            onOpenSafetyProof={() => setCurrentTab('safety')}
          />
        )}

        {currentTab === 'portal' && (
          <CustomerPortalView
            currentUser={selectedUser}
            onNavigateToSupervisor={() => setCurrentTab('supervisor')}
          />
        )}

        {currentTab === 'supervisor' && (
          <SupervisorCommandCenterView
            metrics={metrics}
            onRefreshMetrics={refreshSystemData}
          />
        )}

        {currentTab === 'safety' && (
          <SafetyProofView
            metrics={metrics}
            onRefreshMetrics={refreshSystemData}
          />
        )}
      </main>
    </div>
  );
}

export default App;
