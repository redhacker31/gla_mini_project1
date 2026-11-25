import React, { useState, useEffect, useCallback } from 'react';
import {
  Sliders,
  RefreshCw,
  FileText,
  Compass,
} from 'lucide-react';
import { fetchWhatIfAnalysis, fetchTransactionExplanation } from '../services/api';

export default function ExplainabilityStudio({
  selectedTxnId,
  onClearSelectedTxn,
  onNotify,
}) {
  const [params, setParams] = useState({
    amount: 150.0,
    txn_count_5m: 0.0,
    txn_count_1h: 1.0,
    txn_count_24h: 3.0,
    amount_sum_5m: 0.0,
    amount_sum_1h: 150.0,
    delta_t_seconds: 86400.0,
    recipient_entropy_1h: 0.0,
    amount_deviation_ratio: 1.0,
    recipient_vpa: 'local_kirana@paytm',
    failed_otp_attempts: 0,
  });

  const [isBlacklist, setIsBlacklist] = useState(false);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = React.useRef(null);

  const runSimulation = useCallback(async (currentParams) => {
    setLoading(true);
    try {
      const resp = await fetchWhatIfAnalysis(currentParams);
      setReport(resp);
    } catch (err) {
      console.warn('What-If simulation error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const debouncedRunSimulation = useCallback(
    (currentParams) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        runSimulation(currentParams);
      }, 60);
    },
    [runSimulation]
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    if (selectedTxnId) {
      setLoading(true);
      fetchTransactionExplanation(selectedTxnId)
        .then((resp) => {
          if (mounted && resp) {
            setReport(resp);
            if (resp.features_snapshot) {
              setParams((prev) => ({
                ...prev,
                ...resp.features_snapshot,
              }));
            }
          }
        })
        .catch((err) => {
          if (mounted) {
            onNotify?.(`Failed to load transaction explanation: ${err.message}`, 'error');
          }
        })
        .finally(() => {
          if (mounted) setLoading(false);
        });
    } else {
      runSimulation(params);
    }
    return () => {
      mounted = false;
    };
  }, [selectedTxnId, runSimulation, onNotify]);

  const handleParamChange = (key, value) => {
    const updated = { ...params, [key]: parseFloat(value) || 0 };
    setParams(updated);
    debouncedRunSimulation(updated);
  };

  const handleBlacklistToggle = (checked) => {
    setIsBlacklist(checked);
    const newVpa = checked ? 'attacker_mule4@ybl' : 'local_kirana@paytm';
    const updated = { ...params, recipient_vpa: newVpa };
    setParams(updated);
    runSimulation(updated);
  };

  const applyPreset = (preset) => {
    onClearSelectedTxn?.();
    let newParams = {};
    if (preset === 'benign') {
      newParams = {
        amount: 120.0,
        txn_count_5m: 0.0,
        txn_count_1h: 1.0,
        txn_count_24h: 3.0,
        amount_sum_5m: 0.0,
        amount_sum_1h: 120.0,
        delta_t_seconds: 14400.0,
        recipient_entropy_1h: 0.0,
        amount_deviation_ratio: 0.95,
        recipient_vpa: 'local_kirana@paytm',
        failed_otp_attempts: 0,
      };
      setIsBlacklist(false);
    } else if (preset === 'rapid_fire') {
      newParams = {
        amount: 480.0,
        txn_count_5m: 6.0,
        txn_count_1h: 8.0,
        txn_count_24h: 12.0,
        amount_sum_5m: 1400.0,
        amount_sum_1h: 2200.0,
        delta_t_seconds: 4.2,
        recipient_entropy_1h: 0.65,
        amount_deviation_ratio: 2.4,
        recipient_vpa: 'random_user@upi',
        failed_otp_attempts: 0,
      };
      setIsBlacklist(false);
    } else if (preset === 'smurfing') {
      newParams = {
        amount: 850.0,
        txn_count_5m: 4.0,
        txn_count_1h: 9.0,
        txn_count_24h: 15.0,
        amount_sum_5m: 2400.0,
        amount_sum_1h: 4900.0,
        delta_t_seconds: 35.0,
        recipient_entropy_1h: 2.18,
        amount_deviation_ratio: 3.8,
        recipient_vpa: 'mule_account1@oksbi',
        failed_otp_attempts: 0,
      };
      setIsBlacklist(false);
    } else if (preset === 'blacklist') {
      newParams = {
        amount: 320.0,
        txn_count_5m: 1.0,
        txn_count_1h: 2.0,
        txn_count_24h: 4.0,
        amount_sum_5m: 320.0,
        amount_sum_1h: 550.0,
        delta_t_seconds: 800.0,
        recipient_entropy_1h: 0.0,
        amount_deviation_ratio: 1.1,
        recipient_vpa: 'attacker_mule4@ybl',
        failed_otp_attempts: 0,
      };
      setIsBlacklist(true);
    }
    setParams(newParams);
    runSimulation(newParams);
  };

  const score = report?.composite_score ?? 0;
  const tier = report?.risk_tier ?? 'LOW';
  const mlScore = report?.ml_score ?? 0;
  const sig = report?.sigmoid_decomposition;

  const getTierColor = (t) => {
    if (t === 'LOW') return 'var(--tier-low)';
    if (t === 'MEDIUM') return 'var(--tier-med)';
    return 'var(--tier-high)';
  };

  return (
    <div id="explainability-studio" className="card" style={{ marginBottom: '1.5rem' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: '0.9rem',
        }}
      >
        <div>
          <div className="card-title" style={{ margin: 0 }}>
            <Compass size={18} color="#BE185D" />
            <span>Explainability Lab &amp; What-If Scenario Simulator</span>
            {loading && <RefreshCw size={14} className="spin" color="#E85D3F" />}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {selectedTxnId ? (
              <span>
                Inspecting Persisted Txn: <code style={{ color: 'var(--text-main)', fontWeight: 600 }}>{selectedTxnId}</code>
              </span>
            ) : (
              <span>Interactive Parametric Sensitivity &amp; Feature Waterfall Decomposition</span>
            )}
          </div>
        </div>

        {/* Quick Simulation Presets */}
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
          <button onClick={() => applyPreset('benign')} className="btn btn-outline btn-sm">
            🛒 Legitimate Baseline
          </button>
          <button onClick={() => applyPreset('rapid_fire')} className="btn btn-outline btn-sm">
            ⚡ Rapid-Fire Burst (4s)
          </button>
          <button onClick={() => applyPreset('smurfing')} className="btn btn-outline btn-sm">
            🌊 Mule Smurfing Ring
          </button>
          <button onClick={() => applyPreset('blacklist')} className="btn btn-outline btn-sm">
            🚫 Blacklist Hit
          </button>
          {selectedTxnId && (
            <button onClick={onClearSelectedTxn} className="btn btn-warning btn-sm">
              Clear Txn Filter
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Left = Sliders / Controls, Right = Waterfall & Fusion */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* LEFT COLUMN */}
        <div>
          {/* Live Recalculated Score Card */}
          <div
            style={{
              background: '#FAF8F5',
              border: `2px solid ${getTierColor(tier)}`,
              borderRadius: '12px',
              padding: '1.2rem',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Recalculated Risk Decision
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem', fontFamily: 'var(--font-display)' }}>
                  {tier} RISK TIER
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                  Action: <strong style={{ color: getTierColor(tier) }}>{report?.action}</strong>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>Composite Score S(x)</div>
                <div style={{ fontSize: '2.05rem', fontWeight: 800, color: getTierColor(tier), fontFamily: 'var(--font-display)' }}>
                  {score.toFixed(4)}
                </div>
                <div className="mono" style={{ fontSize: '0.72rem', color: '#BE185D', fontWeight: 600 }}>
                  Isolation Forest S_ml: {mlScore.toFixed(4)}
                </div>
              </div>
            </div>

            {/* Threshold Gauge Bar */}
            <div style={{ marginTop: '0.85rem' }}>
              <div
                style={{
                  height: '9px',
                  borderRadius: '999px',
                  background: '#E5DEC9',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${Math.min(100, Math.max(0, score * 100))}%`,
                    background: getTierColor(tier),
                    borderRadius: '999px',
                    transition: 'width 0.25s ease',
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.3rem', fontWeight: 600 }}>
                <span>0.00 (Low)</span>
                <span style={{ color: 'var(--tier-med)' }}>0.45 Step-Up OTP</span>
                <span style={{ color: 'var(--tier-high)' }}>0.80 Block</span>
                <span>1.00</span>
              </div>
            </div>
          </div>

          {/* Interactive What-If Parameter Sliders */}
          <div className="sub-panel" style={{ padding: '1.2rem', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '1rem' }}>
              <Sliders size={16} color="#E85D3F" />
              <strong style={{ color: 'var(--text-main)', fontFamily: 'var(--font-display)' }}>What-If Parameter Adjustments</strong>
            </div>

            {/* Amount Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Transaction Amount (INR):</span>
                <strong className="mono" style={{ color: 'var(--text-main)' }}>₹{params.amount.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="10"
                max="999"
                step="10"
                value={params.amount}
                onChange={(e) => handleParamChange('amount', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            {/* Delta-T Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Inter-Arrival Delta-T (&Delta;t):</span>
                <strong className="mono" style={{ color: params.delta_t_seconds < 15 ? 'var(--tier-high)' : 'var(--text-main)' }}>
                  {params.delta_t_seconds < 60 ? `${params.delta_t_seconds.toFixed(1)}s (Rapid)` : `${Math.round(params.delta_t_seconds / 60)}m`}
                </strong>
              </div>
              <input
                type="range"
                min="1"
                max="3600"
                step="5"
                value={params.delta_t_seconds}
                onChange={(e) => handleParamChange('delta_t_seconds', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: params.delta_t_seconds < 15 ? 'var(--tier-high)' : 'var(--text-dim)', fontWeight: 500 }}>
                {params.delta_t_seconds < 15 ? '⚠️ <15s triggers RULE_RAPID_FIRE (+0.55 penalty)' : 'Normal inter-arrival spacing'}
              </div>
            </div>

            {/* 5-Min Count Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>5-Minute Transaction Count:</span>
                <strong
                  className="mono"
                  style={{ color: params.txn_count_5m >= 5 ? 'var(--tier-high)' : params.txn_count_5m >= 3 ? 'var(--tier-med)' : 'var(--text-main)' }}
                >
                  {params.txn_count_5m} txns
                </strong>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                step="1"
                value={params.txn_count_5m}
                onChange={(e) => handleParamChange('txn_count_5m', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            {/* Recipient Shannon Entropy Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Recipient Shannon Entropy H(R):</span>
                <strong className="mono" style={{ color: params.recipient_entropy_1h >= 1.8 ? 'var(--tier-high)' : 'var(--text-main)' }}>
                  {params.recipient_entropy_1h.toFixed(2)} bits
                </strong>
              </div>
              <input
                type="range"
                min="0.0"
                max="2.5"
                step="0.05"
                value={params.recipient_entropy_1h}
                onChange={(e) => handleParamChange('recipient_entropy_1h', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: params.recipient_entropy_1h >= 1.8 ? 'var(--tier-high)' : 'var(--text-dim)', fontWeight: 500 }}>
                {params.recipient_entropy_1h >= 1.8 ? '⚠️ H(R) >= 1.8 triggers RULE_RECIPIENT_CHURN (Smurfing)' : 'Normal single-merchant entropy'}
              </div>
            </div>

            {/* Amount Deviation Ratio */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Amount Deviation Ratio:</span>
                <strong className="mono" style={{ color: 'var(--text-main)' }}>{params.amount_deviation_ratio.toFixed(1)}x</strong>
              </div>
              <input
                type="range"
                min="0.5"
                max="8.0"
                step="0.1"
                value={params.amount_deviation_ratio}
                onChange={(e) => handleParamChange('amount_deviation_ratio', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            {/* Blacklist Toggle */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 0.9rem',
                background: isBlacklist ? 'var(--tier-high-bg)' : '#FFFFFF',
                borderRadius: '8px',
                border: `1px solid ${isBlacklist ? 'var(--tier-high-border)' : 'var(--border-color)'}`,
                marginTop: '0.75rem',
              }}
            >
              <div>
                <strong style={{ color: isBlacklist ? 'var(--tier-high)' : 'var(--text-main)' }}>
                  Simulate Blacklisted Mule Syndicate
                </strong>
                <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                  {isBlacklist ? 'VPA: attacker_mule4@ybl (+2.50 CRITICAL)' : 'VPA: local_kirana@paytm (Benign)'}
                </div>
              </div>
              <input
                type="checkbox"
                checked={isBlacklist}
                onChange={(e) => handleBlacklistToggle(e.target.checked)}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div>
          {/* Feature Attribution Waterfall Bars */}
          <div className="sub-panel" style={{ padding: '1.2rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem' }}>
              <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.88rem', fontFamily: 'var(--font-display)' }}>
                Feature Waterfall Attributions (&Delta;S_ml)
              </div>
              <div className="mono" style={{ fontSize: '0.72rem', color: '#BE185D', fontWeight: 600 }}>
                Target ML Anomaly: S_ml = {mlScore.toFixed(3)}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
              {report?.feature_attributions?.map((attr) => {
                const delta = attr.attribution_delta;
                const isRisk = attr.direction === 'RISK_INCREASE';
                const isBenign = attr.direction === 'RISK_DECREASE';
                const barWidth = Math.min(100, Math.abs(delta) * 500);

                return (
                  <div key={attr.feature_name} style={{ fontSize: '0.76rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.18rem' }}>
                      <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{attr.feature_label}</span>
                      <span
                        className="mono"
                        style={{
                          color: isRisk ? 'var(--tier-high)' : isBenign ? 'var(--tier-low)' : 'var(--text-dim)',
                          fontWeight: 700,
                        }}
                      >
                        {delta > 0 ? `+${delta.toFixed(4)}` : delta.toFixed(4)}
                      </span>
                    </div>

                    {/* Waterfall diverging bar */}
                    <div
                      style={{
                        height: '7px',
                        background: '#E5DEC9',
                        borderRadius: '999px',
                        overflow: 'hidden',
                        position: 'relative',
                      }}
                    >
                      <div
                        style={{
                          position: 'absolute',
                          left: isRisk ? '50%' : `${50 - barWidth / 2}%`,
                          width: `${Math.max(4, barWidth / 2)}%`,
                          top: 0,
                          bottom: 0,
                          background: isRisk ? '#EF4444' : isBenign ? '#10B981' : '#8C7F70',
                          borderRadius: '999px',
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.67rem', color: 'var(--text-dim)', marginTop: '0.18rem', gap: '0.5rem' }}>
                      <span>Observed: {attr.observed_value} (Norm: {attr.baseline_value})</span>
                      <span>{attr.description}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sigmoid Fusion Decomposition Formula Box */}
          {sig && (
            <div className="sub-panel" style={{ padding: '1rem', marginBottom: '1.25rem', fontSize: '0.76rem' }}>
              <div style={{ fontWeight: 700, color: '#9D174D', marginBottom: '0.55rem', fontFamily: 'var(--font-display)' }}>
                Mathematical Sigmoid Score Fusion Decomposition:
              </div>

              <div
                className="mono"
                style={{
                  background: '#FFFFFF',
                  border: '1px solid var(--border-color)',
                  padding: '0.8rem',
                  borderRadius: '8px',
                  fontSize: '0.74rem',
                  color: 'var(--text-main)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem',
                }}
              >
                <div>1. Decision Offset (z_0): <strong>{sig.base_theta}</strong></div>
                <div>2. ML Logit Shift (z_ml): {sig.w_ml} &times; ({sig.ml_score} - 0.30) = <strong>+{sig.ml_logit_shift}</strong></div>
                <div>3. Rule Penalties Sum: <strong>+{sig.rule_penalties_sum}</strong></div>
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.35rem', color: 'var(--text-main)' }}>
                  Total Pre-activation Logit: z = <strong>{sig.total_logit_z}</strong>
                </div>
                <div style={{ color: getTierColor(tier), fontWeight: 700 }}>
                  Final Sigmoid: S(x) = 1 / (1 + e^(-{sig.total_logit_z})) = <strong>{sig.composite_score}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Natural Language Analyst Summary */}
          {report?.narrative_summary && (
            <div
              style={{
                background: '#FFFFFF',
                border: '1px solid var(--border-color)',
                borderLeft: `4px solid ${getTierColor(tier)}`,
                borderRadius: '8px',
                padding: '0.9rem 1.05rem',
                fontSize: '0.8rem',
                lineHeight: 1.55,
              }}
            >
              <div style={{ fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <FileText size={14} color={getTierColor(tier)} />
                <span>Executive AI/ML Compliance Briefing:</span>
              </div>
              <p style={{ margin: 0, color: 'var(--text-muted)' }}>{report.narrative_summary}</p>
            </div>
          )}
        </div>
      </div>

      {/* Evaluated Rule Matrix Table */}
      <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
        <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.88rem', marginBottom: '0.75rem', fontFamily: 'var(--font-display)' }}>
          Deterministic Domain Security Rules Audit Matrix ({report?.rule_attributions?.length ?? 0}):
        </div>

        <div className="table-container" style={{ maxHeight: '240px', overflowY: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Rule Identifier</th>
                <th>Rule Name</th>
                <th>Severity</th>
                <th>Penalty Weight</th>
                <th>Audit Evidence / Reason</th>
              </tr>
            </thead>
            <tbody>
              {report?.rule_attributions?.map((r) => (
                <tr key={r.rule_id}>
                  <td>
                    {r.triggered ? (
                      <span className="badge badge-high" style={{ fontSize: '0.65rem' }}>TRIGGERED</span>
                    ) : (
                      <span
                        className="badge"
                        style={{
                          background: 'var(--bg-secondary)',
                          color: 'var(--text-dim)',
                          border: '1px solid var(--border-color)',
                          fontSize: '0.65rem',
                        }}
                      >
                        SAFE
                      </span>
                    )}
                  </td>
                  <td><code style={{ fontWeight: 600 }}>{r.rule_id}</code></td>
                  <td style={{ color: 'var(--text-main)', fontWeight: 600 }}>{r.rule_name}</td>
                  <td>
                    <span
                      style={{
                        color:
                          r.severity === 'CRITICAL' || r.severity === 'HIGH'
                            ? 'var(--tier-high)'
                            : r.severity === 'MEDIUM'
                            ? 'var(--tier-med)'
                            : 'var(--text-dim)',
                        fontWeight: 700,
                        fontSize: '0.72rem',
                      }}
                    >
                      {r.severity}
                    </span>
                  </td>
                  <td className="mono" style={{ fontWeight: 700, color: r.triggered ? 'var(--tier-high)' : 'var(--text-dim)' }}>
                    {r.triggered ? `+${r.penalty.toFixed(2)}` : '0.00'}
                  </td>
                  <td style={{ fontSize: '0.76rem', color: r.triggered ? 'var(--text-main)' : 'var(--text-dim)' }}>
                    {r.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
