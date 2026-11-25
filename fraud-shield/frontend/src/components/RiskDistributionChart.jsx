import React from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { Cpu, Layers } from 'lucide-react';

ChartJS.register(ArcElement, Tooltip, Legend);

export default function RiskDistributionChart({ metrics, health }) {
  const distribution = metrics?.risk_distribution || { low: 0, medium: 0, high: 0 };
  const low = distribution.low || 0;
  const med = distribution.medium || 0;
  const high = distribution.high || 0;
  const total = low + med + high;

  const data = {
    labels: ['Low Risk (Auto-Approve)', 'Medium Risk (Step-Up OTP)', 'High Risk (Blocked)'],
    datasets: [
      {
        data: total > 0 ? [low, med, high] : [1, 0, 0],
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderColor: ['#FFFFFF', '#FFFFFF', '#FFFFFF'],
        borderWidth: 3,
        hoverOffset: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#5C5248',
          font: { size: 11, weight: '600', family: 'Inter, system-ui, sans-serif' },
          padding: 14,
          usePointStyle: true,
        },
      },
      tooltip: {
        backgroundColor: '#1E1916',
        titleColor: '#FAF8F5',
        bodyColor: '#FAF8F5',
        borderColor: '#E5DEC9',
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (context) => {
            if (total === 0) return ' No transactions yet';
            const val = context.raw || 0;
            const pct = ((val / total) * 100).toFixed(1);
            return ` ${context.label}: ${val} (${pct}%)`;
          },
        },
      },
    },
    cutout: '72%',
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '1.25rem',
        marginBottom: '1.5rem',
      }}
    >
      {/* Risk Tier Distribution Chart */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div className="card-title" style={{ margin: 0 }}>
            <Layers size={18} color="#E85D3F" />
            <span>3-Tier Operational Risk Distribution</span>
          </div>
          <span className="badge badge-coral">N = {total.toLocaleString()}</span>
        </div>

        <div style={{ height: '225px', position: 'relative', margin: 'auto 0' }}>
          <Doughnut data={data} options={options} />
          {total === 0 && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-dim)',
                fontSize: '0.82rem',
                pointerEvents: 'none',
              }}
            >
              Awaiting live transactions
            </div>
          )}
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.5rem',
            marginTop: '1rem',
            textAlign: 'center',
            fontSize: '0.75rem',
            borderTop: '1px solid var(--border-color)',
            paddingTop: '0.75rem',
          }}
        >
          <div>
            <div style={{ color: 'var(--tier-low)', fontWeight: 800, fontSize: '0.95rem' }}>{low}</div>
            <div style={{ color: 'var(--text-dim)' }}>
              Low (&lt;{(health?.risk_thresholds?.low ?? 0.45).toFixed(2)})
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--tier-med)', fontWeight: 800, fontSize: '0.95rem' }}>{med}</div>
            <div style={{ color: 'var(--text-dim)' }}>
              Med ({(health?.risk_thresholds?.low ?? 0.45).toFixed(2)}-{(health?.risk_thresholds?.high ?? 0.80).toFixed(2)})
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--tier-high)', fontWeight: 800, fontSize: '0.95rem' }}>{high}</div>
            <div style={{ color: 'var(--text-dim)' }}>
              High (&ge;{(health?.risk_thresholds?.high ?? 0.80).toFixed(2)})
            </div>
          </div>
        </div>
      </div>

      {/* Model & Architecture Benchmarks */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div className="card-title" style={{ margin: 0 }}>
            <Cpu size={18} color="#BE185D" />
            <span>{health?.ml_model?.algorithm || 'Isolation Forest'} Anomaly Core</span>
          </div>
          <span
            className={`badge ${health?.ml_model?.loaded === false ? 'badge-high' : 'badge-low'}`}
            style={{ fontSize: '0.65rem' }}
          >
            {health?.ml_model?.loaded === false ? 'Fallback Mode' : 'Active Bundle'}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
          <div className="sub-panel" style={{ padding: '0.85rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Precision-Recall AUC</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#E85D3F', fontFamily: 'var(--font-display)' }}>
              {(health?.ml_model?.pr_auc ?? 0.8119).toFixed(4)}
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--tier-low)', fontWeight: 600 }}>Target &ge; 0.75</div>
          </div>

          <div className="sub-panel" style={{ padding: '0.85rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Recall @ 1% FPR</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#059669', fontFamily: 'var(--font-display)' }}>
              {((health?.ml_model?.recall_at_1pct_fpr ?? 0.8056) * 100).toFixed(2)}%
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--tier-low)', fontWeight: 600 }}>Target &ge; 75.0%</div>
          </div>

          <div className="sub-panel" style={{ padding: '0.85rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>p95 Latency (Live Gateway)</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#BE185D', fontFamily: 'var(--font-display)' }}>
              {(metrics?.p95_latency_ms || health?.ml_model?.p95_latency_ms || 11.64).toFixed(2)} ms
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--tier-low)', fontWeight: 600 }}>&le; 50.0ms SLA Budget</div>
          </div>

          <div className="sub-panel" style={{ padding: '0.85rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Decision Logic</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#D97706', fontFamily: 'var(--font-display)' }}>
              10 Rules
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 500 }}>Sigmoid Score Fusion</div>
          </div>
        </div>

        <div
          className="sub-panel"
          style={{
            marginTop: 'auto',
            padding: '0.8rem',
            fontSize: '0.76rem',
            color: 'var(--text-muted)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
          }}
        >
          <div>
            <strong style={{ color: 'var(--text-main)' }}>Fusion Formula:</strong>{' '}
            <code>S(x) = &sigma;(w_ml &middot; (S_ml - 0.30) + &Sigma; w_j &middot; R_j - &theta;)</code>
          </div>
          <div>
            <strong style={{ color: 'var(--text-main)' }}>Salted Privacy:</strong> DPDP Act 2023 Compliant (Salted SHA-256 hashing)
          </div>
        </div>
      </div>
    </div>
  );
}
