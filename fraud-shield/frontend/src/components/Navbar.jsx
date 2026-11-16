import React from 'react';
import { 
  Shield, 
  RefreshCw, 
  Database, 
  ExternalLink, 
  Activity,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Navbar({ 
  health, 
  loading, 
  onRefresh, 
  autoRefresh, 
  setAutoRefresh,
  onOpenAuditModal,
  onOpenBenchmarkModal
}) {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="header">
      <div className="logo-area">
        <Shield className="logo-icon" />
        <div>
          <div className="logo-title">
            FRAUD SHIELD
            <span className="logo-badge">CAPSTONE • TEAM 40</span>
          </div>
          <div className="logo-subtitle">
            Real-Time Anomaly Detection for Digital Micro-Transactions &lt; INR 1,000
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
        {/* API Health Badge */}
        <div className={`status-badge ${isHealthy ? 'status-online' : 'status-offline'}`}>
          <span className="pulse-dot"></span>
          <span>{isHealthy ? 'API Gateway Online' : 'API Gateway Offline'}</span>
        </div>

        {/* Database WAL badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          background: 'rgba(30, 41, 59, 0.6)',
          padding: '0.25rem 0.6rem',
          borderRadius: '4px',
          border: '1px solid var(--border-color)',
        }}>
          <Database size={13} color="var(--accent-cyan)" />
          <span>SQLite WAL</span>
        </div>

        {/* Audit Ledger Verify Shortcut */}
        <button
          onClick={onOpenAuditModal}
          className="btn btn-outline btn-sm"
          title="Verify Cryptographic Hash Chain"
        >
          <Shield size={13} color="#10b981" />
          <span>Audit Ledger</span>
        </button>

        {/* Phase 12: SLA Benchmark Shortcut */}
        <button
          onClick={onOpenBenchmarkModal}
          className="btn btn-outline btn-sm"
          title="Inspect Sub-50ms SLA Latency Profiling"
        >
          <Activity size={13} color="#a855f7" />
          <span>SLA &lt;50ms</span>
        </button>

        {/* Auto Refresh Toggle */}
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`btn btn-sm ${autoRefresh ? 'btn-success' : 'btn-outline'}`}
          title="Toggle live 3-second polling"
        >
          <Activity size={13} className={autoRefresh ? 'spin' : ''} />
          <span>{autoRefresh ? 'Live Auto-Polling ON' : 'Auto-Poll Paused'}</span>
        </button>

        {/* Manual Refresh Button */}
        <button 
          onClick={onRefresh}
          disabled={loading}
          className="btn btn-outline btn-sm"
          title="Refresh All Telemetry"
        >
          <RefreshCw size={13} className={loading ? 'spin' : ''} />
          <span>Sync</span>
        </button>

        {/* Swagger Docs Link */}
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-outline btn-sm"
          style={{ textDecoration: 'none' }}
          title="Open FastAPI Swagger Interactive Docs"
        >
          <ExternalLink size={13} />
          <span>API Docs</span>
        </a>
      </div>
    </header>
  );
}
