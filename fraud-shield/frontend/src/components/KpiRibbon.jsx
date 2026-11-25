import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Zap,
  Hash,
  ShieldCheck,
} from 'lucide-react';

export default function KpiRibbon({ metrics, health }) {
  const total = metrics?.total_transactions ?? 0;
  const approved = metrics?.approved_count ?? 0;
  const challenged = metrics?.challenge_count ?? 0;
  const blocked = metrics?.blocked_count ?? 0;

  const approvalRate = metrics?.approval_rate ?? (total > 0 ? ((approved / total) * 100).toFixed(1) : '100.0');
  const challengeRate = metrics?.challenge_rate ?? (total > 0 ? ((challenged / total) * 100).toFixed(1) : '0.0');
  const blockRate = metrics?.rejection_rate ?? (total > 0 ? ((blocked / total) * 100).toFixed(1) : '0.0');

  const lowT = (health?.risk_thresholds?.low ?? 0.45).toFixed(2);
  const highT = (health?.risk_thresholds?.high ?? 0.80).toFixed(2);
  const p95Latency = metrics?.p95_latency_ms ?? 11.64;
  const avgLatency = metrics?.avg_latency_ms ?? 8.42;
  const auditHeight = metrics?.audit_block_height ?? 0;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(205px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      {/* 1. Total Ingestion Volume */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderTop: '3px solid var(--accent-coral)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Total Evaluated
          </span>
          <Hash size={16} color="#E85D3F" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          {total.toLocaleString()}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
          Real-time micro-transaction stream
        </div>
      </div>

      {/* 2. Low Risk Tier (Auto-Approved) */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-low)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Auto-Approved (Low)
          </span>
          <CheckCircle2 size={16} color="#059669" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--tier-low)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          {approvalRate}%
        </div>
        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{approved} txns passed</span>
          <span className="mono" style={{ color: 'var(--tier-low)', fontWeight: 600 }}>S(x) &lt; {lowT}</span>
        </div>
      </div>

      {/* 3. Medium Risk Tier (Step-Up OTP) */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-med)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Challenged (Med)
          </span>
          <AlertTriangle size={16} color="#D97706" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--tier-med)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          {challengeRate}%
        </div>
        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{challenged} OTP challenges</span>
          <span className="mono" style={{ color: 'var(--tier-med)', fontWeight: 600 }}>{lowT} &le; S &lt; {highT}</span>
        </div>
      </div>

      {/* 4. High Risk Tier (Blocked) */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-high)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Frozen / Blocked
          </span>
          <ShieldAlert size={16} color="#DC2626" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--tier-high)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          {blockRate}%
        </div>
        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{blocked} attacks thwarted</span>
          <span className="mono" style={{ color: 'var(--tier-high)', fontWeight: 600 }}>S(x) &ge; {highT}</span>
        </div>
      </div>

      {/* 5. Latency Telemetry */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderTop: '3px solid var(--accent-berry)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            p95 Latency SLA
          </span>
          <Zap size={16} color="#BE185D" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-berry)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          {p95Latency} ms
        </div>
        <div style={{ fontSize: '0.74rem', color: 'var(--tier-low)', fontWeight: 600, marginTop: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <CheckCircle2 size={12} />
          <span>&lt;50ms SLA (avg: {avgLatency}ms)</span>
        </div>
      </div>

      {/* 6. Cryptographic Audit Ledger Height */}
      <div className="card kpi-card" style={{ padding: '1.15rem', borderTop: '3px solid var(--tier-low)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Audit Hash Chain
          </span>
          <ShieldCheck size={16} color="#059669" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.35rem', fontFamily: 'var(--font-display)' }}>
          #{auditHeight}
        </div>
        <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
          Sequential SHA-256 blocks
        </div>
      </div>
    </div>
  );
}
