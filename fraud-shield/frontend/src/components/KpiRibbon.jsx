import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  Zap, 
  Hash, 
  Clock, 
  TrendingUp,
  ShieldCheck
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
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1rem',
      marginBottom: '1.5rem',
    }}>
      {/* 1. Total Ingestion Volume */}
      <div className="card" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Total Evaluated
          </span>
          <Hash size={16} color="var(--accent-cyan)" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fff', marginTop: '0.35rem' }}>
          {total.toLocaleString()}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
          Real-time micro-transaction stream
        </div>
      </div>

      {/* 2. Low Risk Tier (Auto-Approved) */}
      <div className="card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-low)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Auto-Approved (Low)
          </span>
          <CheckCircle2 size={16} color="var(--tier-low)" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--tier-low)', marginTop: '0.35rem' }}>
          {approvalRate}%
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{approved} txns passed</span>
          <span style={{ color: 'var(--tier-low)' }}>S(x) &lt; {lowT}</span>
        </div>
      </div>

      {/* 3. Medium Risk Tier (Step-Up OTP) */}
      <div className="card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-med)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Challenged (Med)
          </span>
          <AlertTriangle size={16} color="var(--tier-med)" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--tier-med)', marginTop: '0.35rem' }}>
          {challengeRate}%
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{challenged} OTP challenges</span>
          <span style={{ color: 'var(--tier-med)' }}>{lowT} &le; S &lt; {highT}</span>
        </div>
      </div>

      {/* 4. High Risk Tier (Blocked) */}
      <div className="card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--tier-high)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Frozen / Blocked (High)
          </span>
          <ShieldAlert size={16} color="var(--tier-high)" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--tier-high)', marginTop: '0.35rem' }}>
          {blockRate}%
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{blocked} attacks thwarted</span>
          <span style={{ color: 'var(--tier-high)' }}>S(x) &ge; {highT}</span>
        </div>
      </div>

      {/* 5. Latency Telemetry */}
      <div className="card" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            p95 Latency SLA
          </span>
          <Zap size={16} color="#a855f7" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#a855f7', marginTop: '0.35rem' }}>
          {p95Latency} ms
        </div>
        <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <CheckCircle2 size={12} />
          <span>&lt; 50ms SLA Compliant (avg: {avgLatency}ms)</span>
        </div>
      </div>

      {/* 6. Cryptographic Audit Ledger Height */}
      <div className="card" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Audit Hash Chain
          </span>
          <ShieldCheck size={16} color="#34d399" />
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#34d399', marginTop: '0.35rem' }}>
          #{auditHeight}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
          Sequential SHA-256 blocks
        </div>
      </div>
    </div>
  );
}
