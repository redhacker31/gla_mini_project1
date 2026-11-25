import React from 'react';
import {
  Shield,
  RefreshCw,
  Database,
  ExternalLink,
  Activity,
  Sparkles,
} from 'lucide-react';

export default function Navbar({
  health,
  loading,
  onRefresh,
  autoRefresh,
  setAutoRefresh,
  onOpenAuditModal,
  onOpenBenchmarkModal,
  onSeedDemo,
  seedingDemo,
}) {
  const isChecking = !health || health?.status === 'checking';
  const isHealthy = health?.status === 'healthy';
  const docsUrl = '/docs';

  return (
    <header className="header">
      <div className="logo-area">
        <Shield className="logo-icon" />
        <div>
          <div className="logo-title">
            FRAUD SHIELD
            <span className="logo-badge">REAL-TIME SOC • TEAM 40</span>
          </div>
          <div className="logo-subtitle">
            Edge-Compatible Anomaly Detection &amp; Step-Up Auth for Micro-Transactions &lt; ₹1,000
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
        {/* API Health Badge */}
        <div
          className={`status-badge ${
            isHealthy ? 'status-online' : isChecking ? 'status-checking' : 'status-offline'
          }`}
        >
          <span className="pulse-dot"></span>
          <span>
            {isHealthy ? 'Gateway Online' : isChecking ? 'Connecting...' : 'Gateway Offline'}
          </span>
        </div>

        {/* Seed Demo Data */}
        {onSeedDemo && (
          <button
            onClick={onSeedDemo}
            disabled={seedingDemo}
            className="btn btn-outline btn-sm"
            title="Populate realistic sample UPI transactions & attacks"
          >
            <Sparkles size={13} color="#fbbf24" className={seedingDemo ? 'spin' : ''} />
            <span>{seedingDemo ? 'Seeding...' : 'Load Demo Traffic'}</span>
          </button>
        )}

        {/* Audit Ledger Verify Shortcut */}
        <button
          onClick={onOpenAuditModal}
          className="btn btn-outline btn-sm"
          title="Verify Cryptographic Hash Chain"
        >
          <Shield size={13} color="#10b981" />
          <span>Audit Ledger</span>
        </button>

        {/* SLA Benchmark Shortcut */}
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
          title="Toggle live auto-polling"
        >
          <Database size={13} />
          <span>{autoRefresh ? 'Live Sync ON' : 'Sync Paused'}</span>
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
          href={docsUrl}
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
