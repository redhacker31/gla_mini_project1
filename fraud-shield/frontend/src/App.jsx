import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle2, AlertTriangle, ShieldAlert, Cpu, Activity, RefreshCw } from 'lucide-react';
import { fetchHealthStatus } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkStatus = async () => {
    setLoading(true);
    const data = await fetchHealthStatus();
    setHealth(data);
    setLoading(false);
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const isHealthy = health?.status === 'healthy';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation */}
      <header className="header">
        <div className="logo-area">
          <Shield className="logo-icon" />
          <div>
            <div className="logo-title">FRAUD SHIELD</div>
            <div className="logo-subtitle">Real-Time Anomaly Detection for Digital Micro-Transactions</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className={`status-badge ${isHealthy ? 'status-online' : 'status-offline'}`}>
            <span className="pulse-dot"></span>
            <span>{isHealthy ? 'Backend API Online' : 'Backend Disconnected'}</span>
          </div>
          <button 
            onClick={checkStatus}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-color)',
              color: 'var(--text-muted)',
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.75rem'
            }}
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container">
        {/* Academic Project Banner */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '1.75rem',
          marginBottom: '2rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <span style={{ 
                fontSize: '0.75rem', 
                textTransform: 'uppercase', 
                letterSpacing: '0.05em', 
                color: 'var(--accent-cyan)',
                fontWeight: 600
              }}>
                B.Tech CSE AIML Capstone Project • Team 40
              </span>
              <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginTop: '0.35rem', color: '#fff' }}>
                Fraud Shield Core Foundation
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginTop: '0.5rem', maxWidth: '750px' }}>
                Phase 1 Project Scaffolding initialized. FastAPI REST backend and React Vite dashboard 
                operational. Ready for Phase 2 dataset ingestion and behavioral feature engineering.
              </p>
            </div>

            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              padding: '1rem 1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              minWidth: '220px'
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Configured Low Threshold</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#34d399' }}>
                S(x) &lt; {health?.risk_thresholds?.low ?? '0.45'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>High Threshold</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f87171' }}>
                S(x) &ge; {health?.risk_thresholds?.high ?? '0.80'}
              </div>
            </div>
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="card-grid">
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <CheckCircle2 color="#10b981" size={20} />
              <div className="card-title" style={{ margin: 0 }}>Low-Risk Tier</div>
            </div>
            <p className="card-desc">
              Scores <strong>S(x) &lt; 0.45</strong>: Legitimate routine commerce passes through frictionlessly 
              with zero added authentication and sub-50ms latency.
            </p>
            <div className="tag-list">
              <span className="tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>Auto-Approve</span>
              <span className="tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>&lt;50ms SLA</span>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <AlertTriangle color="#f59e0b" size={20} />
              <div className="card-title" style={{ margin: 0 }}>Medium-Risk Tier</div>
            </div>
            <p className="card-desc">
              Scores <strong>0.45 &le; S(x) &lt; 0.80</strong>: Triggers Step-Up 6-digit CSPRNG SMS OTP challenge 
              with 180-second TTL and max 3 verification attempts.
            </p>
            <div className="tag-list">
              <span className="tag" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>Step-Up OTP</span>
              <span className="tag" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>180s TTL</span>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <ShieldAlert color="#ef4444" size={20} />
              <div className="card-title" style={{ margin: 0 }}>High-Risk Tier</div>
            </div>
            <p className="card-desc">
              Scores <strong>S(x) &ge; 0.80</strong>: Rapid velocity bursts or smurfing attacks are blocked 
              immediately and flagged for analyst security review.
            </p>
            <div className="tag-list">
              <span className="tag" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>Freeze & Alert</span>
              <span className="tag" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>Anti-Smurfing</span>
            </div>
          </div>
        </div>

        {/* System Health Breakdown */}
        <div style={{ marginTop: '2rem' }} className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Activity color="#3b82f6" size={20} />
            <div className="card-title" style={{ margin: 0 }}>FastAPI Health Status</div>
          </div>

          {health ? (
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              padding: '1rem',
              borderRadius: '6px',
              fontFamily: 'Consolas, monospace',
              fontSize: '0.85rem',
              color: isHealthy ? '#34d399' : '#f87171'
            }}>
              <pre>{JSON.stringify(health, null, 2)}</pre>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Checking endpoint /api/v1/health...
            </p>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        borderTop: '1px solid var(--border-color)',
        padding: '1.25rem',
        textAlign: 'center',
        fontSize: '0.8125rem',
        color: 'var(--text-muted)'
      }}>
        Fraud Shield • GLA University B.Tech AIML Capstone • Phase 1 Foundation Verified
      </footer>
    </div>
  );
}

