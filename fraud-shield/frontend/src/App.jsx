import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, Smartphone, Compass, ShieldCheck } from 'lucide-react';
import Navbar from './components/Navbar';
import KpiRibbon from './components/KpiRibbon';
import RiskDistributionChart from './components/RiskDistributionChart';
import SimulationControl from './components/SimulationControl';
import TransactionEvaluator from './components/TransactionEvaluator';
import LiveTransactionFeed from './components/LiveTransactionFeed';
import ExplainabilityStudio from './components/ExplainabilityStudio';
import SecurityPolicyCenter from './components/SecurityPolicyCenter';
import OtpModal from './components/OtpModal';
import AuditLedgerModal from './components/AuditLedgerModal';
import PerformanceBenchmarkModal from './components/PerformanceBenchmarkModal';
import TransactionDetailModal from './components/TransactionDetailModal';
import {
  fetchHealthStatus,
  fetchDashboardMetrics,
  fetchSimulationStatus,
  fetchTransactions,
  seedDemoTraffic,
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState({ status: 'checking' });
  const [metrics, setMetrics] = useState(null);
  const [simStatus, setSimStatus] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [seedingDemo, setSeedingDemo] = useState(false);

  // Modals & inspector state
  const [otpModal, setOtpModal] = useState({ isOpen: false, sessionId: null, txnId: null });
  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [benchmarkModalOpen, setBenchmarkModalOpen] = useState(false);
  const [inspectedTxn, setInspectedTxn] = useState(null);
  const [selectedTxnForExplain, setSelectedTxnForExplain] = useState(null);

  // Toast notification state
  const [notification, setNotification] = useState(null);
  const toastTimeoutRef = useRef(null);

  const notify = useCallback((message, type = 'info') => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
    }
    setNotification({ message, type, id: Date.now() });
    toastTimeoutRef.current = setTimeout(() => {
      setNotification(null);
    }, 4500);
  }, []);

  // Fetch all live dashboard data
  const refreshData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const [hData, mData, sData, tData] = await Promise.all([
        fetchHealthStatus(),
        fetchDashboardMetrics(),
        fetchSimulationStatus(),
        fetchTransactions(80),
      ]);

      setHealth(hData);
      if (mData) setMetrics(mData);
      if (sData) setSimStatus(sData);
      if (tData && tData.data) {
        setTransactions(tData.data);
      }
    } catch (err) {
      console.warn('Dashboard sync warning:', err);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshData(true);
  }, [refreshData]);

  // Live Auto-Polling Interval (pauses when browser tab is hidden)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      refreshData(false);
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshData]);

  const handleOpenOtpModal = (sessionId, txnId) => {
    setOtpModal({ isOpen: true, sessionId, txnId });
  };

  const handleCloseOtpModal = () => {
    setOtpModal({ isOpen: false, sessionId: null, txnId: null });
  };

  const handleOtpSuccess = () => {
    refreshData(false);
  };

  const handleSelectTxnForExplain = useCallback(
    (txnId) => {
      setSelectedTxnForExplain(txnId);
      setActiveTab('explain');
      notify(`Loaded transaction ${txnId.substring(0, 8)} into Explainability Lab.`, 'info');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [notify]
  );

  const handleSeedDemo = async () => {
    setSeedingDemo(true);
    try {
      const resp = await seedDemoTraffic();
      notify(resp.message || `Seeded ${resp.seeded_count} sample transactions.`, 'success');
      await refreshData(false);
    } catch (err) {
      notify(`Could not seed demo data: ${err.message}`, 'error');
    } finally {
      setSeedingDemo(false);
    }
  };

  const pendingCount = metrics?.challenge_count ?? 0;
  const flaggedCount = metrics?.blocked_count ?? 0;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <Navbar
        health={health}
        loading={loading}
        onRefresh={() => refreshData(true)}
        autoRefresh={autoRefresh}
        setAutoRefresh={setAutoRefresh}
        onOpenAuditModal={() => setAuditModalOpen(true)}
        onOpenBenchmarkModal={() => setBenchmarkModalOpen(true)}
        onSeedDemo={handleSeedDemo}
        seedingDemo={seedingDemo}
      />

      {/* Main Dashboard Workspace */}
      <main className="container">
        {/* Workspace Navigation Tabs */}
        <nav className="workspace-tabs" aria-label="Primary sections">
          <button
            type="button"
            className={`workspace-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={16} />
            <span>SOC Live Monitor</span>
            {(pendingCount > 0 || flaggedCount > 0) && (
              <span
                style={{
                  background: activeTab === 'overview' ? 'rgba(255, 255, 255, 0.24)' : 'var(--tier-med-bg)',
                  color: activeTab === 'overview' ? '#FFFFFF' : 'var(--tier-med)',
                  border: activeTab === 'overview' ? 'none' : '1px solid var(--tier-med-border)',
                  padding: '0.08rem 0.5rem',
                  borderRadius: '999px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                }}
              >
                {pendingCount + flaggedCount} alerts
              </span>
            )}
          </button>

          <button
            type="button"
            className={`workspace-tab ${activeTab === 'sandbox' ? 'active' : ''}`}
            onClick={() => setActiveTab('sandbox')}
          >
            <Smartphone size={16} />
            <span>UPI Payment Sandbox</span>
          </button>

          <button
            type="button"
            className={`workspace-tab ${activeTab === 'explain' ? 'active' : ''}`}
            onClick={() => setActiveTab('explain')}
          >
            <Compass size={16} />
            <span>Explainability &amp; What-If Lab</span>
            {selectedTxnForExplain && (
              <span
                style={{
                  background: activeTab === 'explain' ? 'rgba(255, 255, 255, 0.24)' : 'var(--accent-plum-tint)',
                  color: activeTab === 'explain' ? '#FFFFFF' : 'var(--accent-plum)',
                  border: activeTab === 'explain' ? 'none' : '1px solid var(--accent-plum-border)',
                  padding: '0.08rem 0.5rem',
                  borderRadius: '999px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                }}
              >
                Txn Loaded
              </span>
            )}
          </button>

          <button
            type="button"
            className={`workspace-tab ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            <ShieldCheck size={16} />
            <span>Security &amp; Blacklist Policy</span>
          </button>
        </nav>

        {/* TAB 1: SOC Live Monitor */}
        {activeTab === 'overview' && (
          <>
            <KpiRibbon metrics={metrics} health={health} />
            <RiskDistributionChart metrics={metrics} health={health} />
            <SimulationControl
              simStatus={simStatus}
              onRefresh={() => refreshData(false)}
              onNotify={notify}
            />
            <LiveTransactionFeed
              transactions={transactions}
              loading={loading}
              onRefresh={() => refreshData(true)}
              onOpenOtpModal={handleOpenOtpModal}
              onSelectTxnForExplain={handleSelectTxnForExplain}
              onInspectTxn={(txn) => setInspectedTxn(txn)}
            />
          </>
        )}

        {/* TAB 2: Interactive UPI Payment Sandbox */}
        {activeTab === 'sandbox' && (
          <>
            <TransactionEvaluator
              thresholds={health?.risk_thresholds}
              onTransactionEvaluated={() => refreshData(false)}
              onOpenOtpModal={handleOpenOtpModal}
              onInspectInExplainability={handleSelectTxnForExplain}
              onNotify={notify}
            />
            <LiveTransactionFeed
              transactions={transactions.slice(0, 15)}
              loading={loading}
              onRefresh={() => refreshData(true)}
              onOpenOtpModal={handleOpenOtpModal}
              onSelectTxnForExplain={handleSelectTxnForExplain}
              onInspectTxn={(txn) => setInspectedTxn(txn)}
            />
          </>
        )}

        {/* TAB 3: Explainability & What-If Studio */}
        {activeTab === 'explain' && (
          <ExplainabilityStudio
            selectedTxnId={selectedTxnForExplain}
            onClearSelectedTxn={() => setSelectedTxnForExplain(null)}
            onNotify={notify}
          />
        )}

        {/* TAB 4: Security & Blacklist Policy Console */}
        {activeTab === 'security' && (
          <SecurityPolicyCenter
            onPolicyUpdated={() => refreshData(false)}
            onNotify={notify}
          />
        )}
      </main>

      {/* Transaction Detail & Analyst Review Modal */}
      {inspectedTxn && (
        <TransactionDetailModal
          transaction={inspectedTxn}
          onClose={() => setInspectedTxn(null)}
          onOpenOtpModal={handleOpenOtpModal}
          onSelectTxnForExplain={handleSelectTxnForExplain}
          onReviewed={() => refreshData(false)}
          onNotify={notify}
        />
      )}

      {/* Step-Up OTP Verification Modal */}
      {otpModal.isOpen && (
        <OtpModal
          sessionId={otpModal.sessionId}
          txnId={otpModal.txnId}
          onClose={handleCloseOtpModal}
          onSuccess={handleOtpSuccess}
          onNotify={notify}
        />
      )}

      {/* Cryptographic Audit Ledger Modal */}
      {auditModalOpen && (
        <AuditLedgerModal
          onClose={() => setAuditModalOpen(false)}
          onNotify={notify}
        />
      )}

      {/* Sub-50ms SLA Benchmark Modal */}
      {benchmarkModalOpen && (
        <PerformanceBenchmarkModal
          onClose={() => setBenchmarkModalOpen(false)}
          onNotify={notify}
        />
      )}

      {/* Warm High-Contrast Toast Notification */}
      {notification && (
        <div
          style={{
            position: 'fixed',
            bottom: '1.5rem',
            right: '1.5rem',
            padding: '0.85rem 1.25rem',
            borderRadius: '10px',
            background:
              notification.type === 'success'
                ? '#ECFDF5'
                : notification.type === 'error'
                ? '#FEF2F2'
                : '#FFF1ED',
            border: `1px solid ${
              notification.type === 'success'
                ? '#A7F3D0'
                : notification.type === 'error'
                ? '#FECACA'
                : '#FBC7BA'
            }`,
            color:
              notification.type === 'success'
                ? '#059669'
                : notification.type === 'error'
                ? '#DC2626'
                : '#D14628',
            fontWeight: 600,
            fontSize: '0.825rem',
            boxShadow: 'var(--shadow-md)',
            zIndex: 999,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            animation: 'fadeIn 0.2s ease',
          }}
        >
          <span>{notification.message}</span>
        </div>
      )}

      {/* Footer */}
      <footer
        style={{
          marginTop: 'auto',
          borderTop: '1px solid var(--border-color)',
          padding: '1.25rem 2rem',
          textAlign: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          background: 'var(--bg-secondary)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', maxWidth: '1380px', margin: '0 auto' }}>
          <span><strong style={{ color: 'var(--text-main)' }}>Fraud Shield</strong> • Edge-Compatible Real-Time Anomaly Detection</span>
          <span>B.Tech CSE AIML Capstone Project • GLA University • Team 40</span>
          <span>DPDP Act 2023 Compliant • Sub-50ms SLA Guaranteed</span>
        </div>
      </footer>
    </div>
  );
}
