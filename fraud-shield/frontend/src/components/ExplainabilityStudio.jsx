import React, { useState, useEffect, useCallback } from 'react';
import { 
  Cpu, 
  HelpCircle, 
  Layers, 
  Sliders, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  Zap, 
  RefreshCw, 
  ArrowRight,
  TrendingUp,
  FileText,
  Lock,
  Compass
} from 'lucide-react';
import { fetchWhatIfAnalysis, fetchTransactionExplanation } from '../services/api';

export default function ExplainabilityStudio({ 
  selectedTxnId, 
  onClearSelectedTxn,
  onNotify 
}) {
  // Simulator input parameters
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

  // Run What-If simulation
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

  // When selectedTxnId changes, fetch explanation for that specific persisted transaction
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
    return () => { mounted = false; };
  }, [selectedTxnId, runSimulation, onNotify]);

  // Handle slider changes
  const handleParamChange = (key, value) => {
    const updated = { ...params, [key]: parseFloat(value) || 0 };
    setParams(updated);
    runSimulation(updated);
  };

  // Toggle blacklist
  const handleBlacklistToggle = (checked) => {
    setIsBlacklist(checked);
    const newVpa = checked ? 'attacker_mule4@ybl' : 'local_kirana@paytm';
    const updated = { ...params, recipient_vpa: newVpa };
    setParams(updated);
    runSimulation(updated);
  };

  // Apply Quick Simulation Presets
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
        delta_t_seconds: 14400.0, // 4 hours
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
        delta_t_seconds: 4.2, // 4.2 seconds
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
        recipient_entropy_1h: 2.18, // High entropy
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
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.25rem',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.85rem',
      }}>
        <div>
          <div className="card-title" style={{ margin: 0 }}>
            <Compass size={18} color="var(--accent-cyan)" />
            <span>Phase 11: Explainability Studio & What-If Scenario Simulator</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {selectedTxnId ? (
              <span>Inspecting Persisted Txn: <code style={{ color: '#fff' }}>{selectedTxnId}</code></span>
            ) : (
              <span>Interactive Parametric Sensitivity & Feature Waterfall Decomposition</span>
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
        
        {/* LEFT COLUMN: What-If Parameter Sliders & Live Decision */}
        <div>
          {/* Live Recalculated Score Card */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: `1px solid ${getTierColor(tier)}`,
            borderRadius: '8px',
            padding: '1.15rem',
            marginBottom: '1.25rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Recalculated Risk Decision
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                  {tier} RISK TIER
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.15rem' }}>
                  Action: <strong style={{ color: getTierColor(tier) }}>{report?.action}</strong>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Composite Score S(x)</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: getTierColor(tier) }}>
                  {score.toFixed(4)}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#38bdf8' }}>
                  Isolation Forest S_ml: {mlScore.toFixed(4)}
                </div>
              </div>
            </div>

            {/* Threshold Gauge Bar */}
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{
                height: '8px',
                borderRadius: '4px',
                background: '#1e293b',
                position: 'relative',
                overflow: 'hidden',
              }}>
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${Math.min(100, Math.max(0, score * 100))}%`,
                  background: getTierColor(tier),
                  borderRadius: '4px',
                  transition: 'width 0.25s ease',
                }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                <span>0.00 (Low)</span>
                <span style={{ color: 'var(--tier-med)' }}>0.45 Threshold (Step-Up OTP)</span>
                <span style={{ color: 'var(--tier-high)' }}>0.80 Threshold (Block)</span>
                <span>1.00</span>
              </div>
            </div>
          </div>

          {/* Interactive What-If Parameter Sliders */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '1.15rem',
            fontSize: '0.8rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
              <Sliders size={16} color="var(--accent-cyan)" />
              <strong style={{ color: '#fff' }}>What-If Parameter Adjustments</strong>
            </div>

            {/* Amount Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Transaction Amount (INR):</span>
                <strong style={{ color: '#fff' }}>₹{params.amount.toFixed(2)}</strong>
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

            {/* Delta-T Slider (Log-scale friendly: 1s to 7200s) */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Inter-Arrival Delta-T (Δt):</span>
                <strong style={{ color: params.delta_t_seconds < 15 ? '#ef4444' : '#fff' }}>
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
              <div style={{ fontSize: '0.65rem', color: params.delta_t_seconds < 15 ? '#f87171' : 'var(--text-dim)' }}>
                {params.delta_t_seconds < 15 ? '⚠️ <15s triggers RULE_RAPID_FIRE (+0.55 penalty)' : 'Normal inter-arrival spacing'}
              </div>
            </div>

            {/* 5-Min Count Slider */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>5-Minute Transaction Count:</span>
                <strong style={{ color: params.txn_count_5m >= 5 ? '#ef4444' : params.txn_count_5m >= 3 ? '#f59e0b' : '#fff' }}>
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
                <span style={{ color: 'var(--text-muted)' }}>Recipient Shannon Entropy H(R):</span>
                <strong style={{ color: params.recipient_entropy_1h >= 1.8 ? '#ef4444' : '#fff' }}>
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
              <div style={{ fontSize: '0.65rem', color: params.recipient_entropy_1h >= 1.8 ? '#f87171' : 'var(--text-dim)' }}>
                {params.recipient_entropy_1h >= 1.8 ? '⚠️ H(R) >= 1.8 triggers RULE_RECIPIENT_CHURN (Smurfing)' : 'Normal single-merchant entropy'}
              </div>
            </div>

            {/* Amount Deviation Ratio */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Amount Deviation Ratio:</span>
                <strong style={{ color: '#fff' }}>{params.amount_deviation_ratio.toFixed(1)}x</strong>
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
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.65rem 0.85rem',
              background: isBlacklist ? 'rgba(239, 68, 68, 0.15)' : 'rgba(0, 0, 0, 0.2)',
              borderRadius: '6px',
              border: `1px solid ${isBlacklist ? '#ef4444' : 'var(--border-color)'}`,
              marginTop: '0.75rem',
            }}>
              <div>
                <strong style={{ color: isBlacklist ? '#f87171' : '#fff' }}>
                  Simulate Blacklisted Mule Syndicate
                </strong>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
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

        {/* RIGHT COLUMN: SHAP-Style Feature Waterfall & Sigmoid Decomposition */}
        <div>
          {/* Feature Attribution Waterfall Bars */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '1.15rem',
            marginBottom: '1.25rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
              <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>
                Feature Waterfall Attributions (ΔS_ml)
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                Target ML Anomaly: S_ml = {mlScore.toFixed(3)}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {report?.feature_attributions?.map((attr) => {
                const delta = attr.attribution_delta;
                const isRisk = attr.direction === 'RISK_INCREASE';
                const isBenign = attr.direction === 'RISK_DECREASE';
                const barWidth = Math.min(100, Math.abs(delta) * 500); // Scale for visual impact

                return (
                  <div key={attr.feature_name} style={{ fontSize: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.15rem' }}>
                      <span style={{ color: '#fff', fontWeight: 500 }}>{attr.feature_label}</span>
                      <span style={{ color: isRisk ? '#f87171' : isBenign ? '#34d399' : 'var(--text-dim)', fontWeight: 700 }}>
                        {delta > 0 ? `+${delta.toFixed(4)}` : delta.toFixed(4)}
                      </span>
                    </div>

                    {/* Waterfall diverging bar */}
                    <div style={{
                      height: '6px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                      position: 'relative',
                    }}>
                      <div style={{
                        position: 'absolute',
                        left: isRisk ? '50%' : `${50 - barWidth / 2}%`,
                        width: `${Math.max(4, barWidth / 2)}%`,
                        top: 0,
                        bottom: 0,
                        background: isRisk ? '#ef4444' : isBenign ? '#10b981' : 'var(--text-dim)',
                        borderRadius: '3px',
                      }} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.15rem' }}>
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
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
              marginBottom: '1.25rem',
              fontSize: '0.75rem',
            }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
                Mathematical Sigmoid Score Fusion Decomposition:
              </div>

              <div style={{
                background: 'rgba(0, 0, 0, 0.35)',
                padding: '0.75rem',
                borderRadius: '6px',
                fontFamily: 'Consolas, monospace',
                fontSize: '0.75rem',
                color: '#e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.35rem',
              }}>
                <div>1. Decision Offset (z_0): <strong>{sig.base_theta}</strong></div>
                <div>2. ML Logit Shift (z_ml): {sig.w_ml} &times; ({sig.ml_score} - 0.30) = <strong>+{sig.ml_logit_shift}</strong></div>
                <div>3. Rule Penalties Sum: <strong>+{sig.rule_penalties_sum}</strong></div>
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.35rem', color: '#fff' }}>
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
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              borderLeft: `4px solid ${getTierColor(tier)}`,
              borderRadius: '0 6px 6px 0',
              padding: '0.85rem 1rem',
              fontSize: '0.8rem',
              lineHeight: 1.5,
              color: 'var(--text-main)',
            }}>
              <div style={{ fontWeight: 600, color: '#fff', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
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
        <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
          Deterministic Domain Security Rules Audit Matrix ({report?.rule_attributions?.length ?? 0}):
        </div>

        <div className="table-container" style={{ maxHeight: '220px', overflowY: 'auto' }}>
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
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)', fontSize: '0.65rem' }}>
                        SAFE
                      </span>
                    )}
                  </td>
                  <td><code>{r.rule_id}</code></td>
                  <td style={{ color: '#fff', fontWeight: 500 }}>{r.rule_name}</td>
                  <td>
                    <span style={{
                      color: r.severity === 'CRITICAL' ? '#ef4444' : r.severity === 'HIGH' ? '#f87171' : r.severity === 'MEDIUM' ? '#fbbf24' : '#94a3b8',
                      fontWeight: 700,
                      fontSize: '0.7rem',
                    }}>
                      {r.severity}
                    </span>
                  </td>
                  <td style={{ fontWeight: 700, color: r.triggered ? '#f87171' : 'var(--text-dim)' }}>
                    {r.triggered ? `+${r.penalty.toFixed(2)}` : '0.00'}
                  </td>
                  <td style={{ fontSize: '0.75rem', color: r.triggered ? '#fff' : 'var(--text-dim)' }}>
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
