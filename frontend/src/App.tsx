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
  const [visitedTabs, setVisitedTabs] = useState(() => new Set([currentTab]));
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  // Keep visited views mounted so navigation preserves state and in-flight work.
  const handleTabChange = (tab: typeof currentTab) => {
    setVisitedTabs((prev) => prev.has(tab) ? prev : new Set([...prev, tab]));
    setCurrentTab(tab);
  };

  const refreshSystemData = useCallback(async () => {
    try {
      const health = await fetchHealth();
      setBackendOnline(health.status === 'ok');

      const [usersData, metricsData, approvalsData] = await Promise.all([
        fetchDemoUsers(),
        fetchMetrics(),
        fetchApprovals('pending')
      ]);

      setSelectedUser((prev) => prev || usersData.find((user) => user.user_id === 'user_1') || usersData[0] || null);
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
    <div className="min-h-screen bg-[#FAFAF9] text-[#1C1917] flex flex-col bg-grid-pattern selection:bg-[#C2410C] selection:text-white font-sans">
      {/* Top Navigation */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={handleTabChange}
        pendingApprovalsCount={pendingApprovalsCount}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
        backendOnline={backendOnline}
      />

      {/* Main Content View */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        <div hidden={currentTab !== 'landing'}>
          {visitedTabs.has('landing') && (
            <LandingView
              metrics={metrics}
              onLaunchDemo={() => handleTabChange('portal')}
              onOpenCommandCenter={() => handleTabChange('supervisor')}
              onOpenSafetyProof={() => handleTabChange('safety')}
            />
          )}
        </div>

        <div hidden={currentTab !== 'portal'}>
          {visitedTabs.has('portal') && (
            <CustomerPortalView
              currentUser={selectedUser}
              onNavigateToSupervisor={() => handleTabChange('supervisor')}
            />
          )}
        </div>

        <div hidden={currentTab !== 'supervisor'}>
          {visitedTabs.has('supervisor') && (
            <SupervisorCommandCenterView
              metrics={metrics}
              onRefreshMetrics={refreshSystemData}
            />
          )}
        </div>

        <div hidden={currentTab !== 'safety'}>
          {visitedTabs.has('safety') && (
            <SafetyProofView
              metrics={metrics}
              onRefreshMetrics={refreshSystemData}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
