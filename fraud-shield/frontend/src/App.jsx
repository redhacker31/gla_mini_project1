import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './components/Navbar';
import KpiRibbon from './components/KpiRibbon';
import RiskDistributionChart from './components/RiskDistributionChart';
import SimulationControl from './components/SimulationControl';
import TransactionEvaluator from './components/TransactionEvaluator';
import LiveTransactionFeed from './components/LiveTransactionFeed';
import ExplainabilityStudio from './components/ExplainabilityStudio';
import OtpModal from './components/OtpModal';
import AuditLedgerModal from './components/AuditLedgerModal';
import PerformanceBenchmarkModal from './components/PerformanceBenchmarkModal';
import { 
  fetchHealthStatus, 
  fetchDashboardMetrics, 
  fetchSimulationStatus, 
  fetchTransactions 
} from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [simStatus, setSimStatus] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Modals state
  const [otpModal, setOtpModal] = useState({ isOpen: false, sessionId: null, txnId: null });
  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [benchmarkModalOpen, setBenchmarkModalOpen] = useState(false);
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
        fetchTransactions(50),
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

  // Live Auto-Polling Interval (every 3.5s)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      refreshData(false);
    }, 3500);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshData]);

  // Handlers for OTP modal
  const handleOpenOtpModal = (sessionId, txnId) => {
    setOtpModal({ isOpen: true, sessionId, txnId });
  };

  const handleCloseOtpModal = () => {
    setOtpModal({ isOpen: false, sessionId: null, txnId: null });
  };

  const handleOtpSuccess = () => {
    refreshData(false);
  };

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
      />

      {/* Main Dashboard Workspace */}
      <main className="container">
        {/* Top KPI Telemetry Ribbon */}
        <KpiRibbon metrics={metrics} health={health} />

        {/* 3-Tier Risk Distribution Chart & Model Telemetry */}
        <RiskDistributionChart metrics={metrics} health={health} />

        {/* Adversarial Simulation & Streaming Controls */}
        <SimulationControl
          simStatus={simStatus}
          onRefresh={() => refreshData(false)}
          onNotify={notify}
        />

        {/* Real-Time Transaction Evaluator Form & Result Card */}
        <TransactionEvaluator
          onTransactionEvaluated={() => refreshData(false)}
          onOpenOtpModal={handleOpenOtpModal}
          onNotify={notify}
        />

        {/* Phase 11: Explainability Studio & What-If Scenario Simulator */}
        <ExplainabilityStudio
          selectedTxnId={selectedTxnForExplain}
          onClearSelectedTxn={() => setSelectedTxnForExplain(null)}
          onNotify={notify}
        />

        {/* Live Evaluated Transactions Stream Table */}
        <LiveTransactionFeed
          transactions={transactions}
          loading={loading}
          onRefresh={() => refreshData(true)}
          onOpenOtpModal={handleOpenOtpModal}
          onSelectTxnForExplain={(txnId) => {
            setSelectedTxnForExplain(txnId);
            notify(`Loaded transaction ${txnId.substring(0, 8)} into Explainability Studio.`, 'info');
          }}
        />
      </main>

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

      {/* Phase 12: Performance & SLA Benchmark Modal */}
      {benchmarkModalOpen && (
        <PerformanceBenchmarkModal
          onClose={() => setBenchmarkModalOpen(false)}
          onNotify={notify}
        />
      )}

      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          padding: '0.75rem 1.25rem',
          borderRadius: '8px',
          background: 
            notification.type === 'success' ? '#064e3b' :
            notification.type === 'error' ? '#7f1d1d' : '#1e293b',
          border: `1px solid ${
            notification.type === 'success' ? '#10b981' :
            notification.type === 'error' ? '#ef4444' : '#3b82f6'
          }`,
          color: '#fff',
          fontSize: '0.825rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          animation: 'fadeIn 0.2s ease',
        }}>
          <span>{notification.message}</span>
        </div>
      )}

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        borderTop: '1px solid var(--border-color)',
        padding: '1.25rem 2rem',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: 'var(--text-muted)',
        background: 'rgba(15, 23, 42, 0.5)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', maxWidth: '1380px', margin: '0 auto' }}>
          <span><strong>Fraud Shield</strong> • Edge-Compatible Real-Time Anomaly Detection</span>
          <span>B.Tech CSE AIML Capstone Project • GLA University • Team 40</span>
          <span>DPDP Act 2023 Compliant • Sub-50ms SLA Guaranteed</span>
        </div>
      </footer>
    </div>
  );
}
