import React, { useState } from 'react';
import { 
  Send, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  Clock, 
  Zap, 
  Lock, 
  Layers, 
  FileCode,
  ShieldCheck
} from 'lucide-react';
import { evaluateTransaction } from '../services/api';

export default function TransactionEvaluator({ 
  onTransactionEvaluated, 
  onOpenOtpModal,
  onNotify 
}) {
  const [formData, setFormData] = useState({
    user_id: 'user_ramesh_rural_01',
    amount: '150.00',
    recipient_vpa: 'local_kirana@paytm',
    merchant_category: 'grocery',
    channel: 'upi_qr',
    device_id: 'dev_android_102',
  });

  const [loading, setLoading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);

  const applyPreset = (preset) => {
    if (preset === 'routine') {
      setFormData({
        user_id: 'user_ramesh_rural_01',
        amount: '120.00',
        recipient_vpa: 'local_kirana@paytm',
        merchant_category: 'grocery',
        channel: 'upi_qr',
        device_id: 'dev_android_102',
      });
    } else if (preset === 'velocity') {
      setFormData({
        user_id: 'user_ramesh_rural_01',
        amount: '480.00',
        recipient_vpa: 'suspicious_mule_01@ybl',
        merchant_category: 'p2p_transfer',
        channel: 'mobile_app',
        device_id: 'dev_unknown_999',
      });
    } else if (preset === 'smurfing') {
      setFormData({
        user_id: 'user_smurf_syndicate',
        amount: '990.00',
        recipient_vpa: 'layering_aggregator@icici',
        merchant_category: 'p2p_transfer',
        channel: 'mobile_app',
        device_id: 'dev_emulator_v3',
      });
    } else if (preset === 'blacklist') {
      setFormData({
        user_id: 'user_targeted_victim',
        amount: '350.00',
        recipient_vpa: 'blacklisted_mule99@upi',
        merchant_category: 'miscellaneous',
        channel: 'mobile_app',
        device_id: 'dev_android_456',
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setEvalResult(null);

    const payload = {
      user_id: formData.user_id,
      amount: parseFloat(formData.amount),
      recipient_id: formData.recipient_vpa,
      recipient_vpa: formData.recipient_vpa,
      merchant_category: formData.merchant_category,
      channel: formData.channel,
      device_id: formData.device_id,
    };

    try {
      const response = await evaluateTransaction(payload);
      setEvalResult(response);
      onNotify?.(`Transaction ${response.txn_id.substring(0, 8)} evaluated: ${response.status}`, 'info');
      onTransactionEvaluated?.(response);
    } catch (err) {
      onNotify?.(`Evaluation failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const getTierColor = (tier) => {
    if (tier === 'LOW') return 'var(--tier-low)';
    if (tier === 'MEDIUM') return 'var(--tier-med)';
    return 'var(--tier-high)';
  };

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <Zap size={18} color="var(--accent-cyan)" />
          <span>Real-Time Transaction Risk Evaluation Gateway</span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Sub-50ms SLA Target • Edge-Compatible CPU Inference
        </div>
      </div>

      {/* Quick Presets Ribbon */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Presets:</span>
        <button type="button" onClick={() => applyPreset('routine')} className="btn btn-outline btn-sm">
          🛒 Benign Kirana (₹120)
        </button>
        <button type="button" onClick={() => applyPreset('velocity')} className="btn btn-outline btn-sm">
          ⚡ Rapid-Fire Burst (₹480)
        </button>
        <button type="button" onClick={() => applyPreset('smurfing')} className="btn btn-outline btn-sm">
          🌊 Mule Smurfing (₹990)
        </button>
        <button type="button" onClick={() => applyPreset('blacklist')} className="btn btn-outline btn-sm">
          🚫 Blacklisted Mule (₹350)
        </button>
      </div>

      {/* Ingestion Form */}
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.85rem' }}>
          <div className="form-group">
            <label className="form-label">User Identifier</label>
            <input
              type="text"
              className="form-input"
              value={formData.user_id}
              onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Amount (INR &lt; 1000)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="999.99"
              className="form-input"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Recipient VPA / Merchant</label>
            <input
              type="text"
              className="form-input"
              value={formData.recipient_vpa}
              onChange={(e) => setFormData({ ...formData, recipient_vpa: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Merchant Category</label>
            <select
              className="form-select"
              value={formData.merchant_category}
              onChange={(e) => setFormData({ ...formData, merchant_category: e.target.value })}
            >
              <option value="grocery">Grocery & Supermarket</option>
              <option value="food_dining">Food & Tea Stall</option>
              <option value="utilities">Utilities & Recharges</option>
              <option value="transport">Local Transport / Auto</option>
              <option value="p2p_transfer">Peer-to-Peer (P2P)</option>
              <option value="miscellaneous">Miscellaneous</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Channel</label>
            <select
              className="form-select"
              value={formData.channel}
              onChange={(e) => setFormData({ ...formData, channel: e.target.value })}
            >
              <option value="upi_qr">UPI Static / Dynamic QR</option>
              <option value="mobile_app">Mobile App Direct</option>
              <option value="web_checkout">Web Checkout</option>
              <option value="pos">POS Terminal</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Device Identifier</label>
            <input
              type="text"
              className="form-input"
              value={formData.device_id}
              onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.75rem' }}>
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? <Zap size={14} className="spin" /> : <Send size={14} />}
            <span>{loading ? 'Evaluating Risk & Model...' : 'Evaluate Micro-Transaction Risk'}</span>
          </button>
        </div>
      </form>

      {/* Evaluation Result Card */}
      {evalResult && (
        <div style={{
          marginTop: '1.5rem',
          background: 'rgba(15, 23, 42, 0.9)',
          borderRadius: '8px',
          border: `1px solid ${getTierColor(evalResult.risk_tier)}`,
          padding: '1.25rem',
          animation: 'fadeIn 0.25s ease',
        }}>
          {/* Header of Evaluation */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
            borderBottom: '1px solid var(--border-color)',
            paddingBottom: '0.85rem',
            marginBottom: '1rem',
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Evaluated Txn ID: <code style={{ color: '#fff' }}>{evalResult.txn_id}</code>
              </div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                ₹{evalResult.amount?.toFixed(2)} &rarr; {evalResult.recipient_vpa_masked || formData.recipient_vpa}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                Salted DPDP Hash: <code>{evalResult.user_hash?.substring(0, 16)}...</code>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Composite Risk Score S(x)</div>
              <div style={{ fontSize: '1.85rem', fontWeight: 800, color: getTierColor(evalResult.risk_tier) }}>
                {evalResult.composite_score?.toFixed(4)}
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                <span className={`badge ${
                  evalResult.risk_tier === 'LOW' ? 'badge-low' :
                  evalResult.risk_tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                }`}>
                  {evalResult.risk_tier} RISK
                </span>
                <span className={`badge ${
                  evalResult.status === 'APPROVED' ? 'badge-approved' :
                  evalResult.status === 'PENDING_VERIFICATION' ? 'badge-pending' : 'badge-rejected'
                }`}>
                  {evalResult.status}
                </span>
              </div>
            </div>
          </div>

          {/* Score Meter Bar */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              <span>Low Risk (0.00 - 0.45)</span>
              <span>Medium Risk (0.45 - 0.80)</span>
              <span>High Risk (0.80 - 1.00)</span>
            </div>
            <div style={{
              height: '8px',
              borderRadius: '4px',
              background: '#1e293b',
              overflow: 'hidden',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: `${Math.min(100, Math.max(0, evalResult.composite_score * 100))}%`,
                background: getTierColor(evalResult.risk_tier),
                borderRadius: '4px',
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>

          {/* Latency and Scores Breakdown */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '0.75rem',
            background: 'rgba(0, 0, 0, 0.25)',
            padding: '0.75rem',
            borderRadius: '6px',
            fontSize: '0.8rem',
            marginBottom: '1rem',
          }}>
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Isolation Forest Score</div>
              <div style={{ fontWeight: 700, color: '#38bdf8' }}>{evalResult.ml_score?.toFixed(4)}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Total Latency Budget</div>
              <div style={{ fontWeight: 700, color: '#34d399' }}>{evalResult.latency_ms?.toFixed(2)} ms (&lt;50ms)</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Operational Action</div>
              <div style={{ fontWeight: 700, color: '#fff' }}>{evalResult.action}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Step-Up Challenge</div>
              <div style={{ fontWeight: 700, color: evalResult.challenge_required ? '#fbbf24' : '#10b981' }}>
                {evalResult.challenge_required ? 'Required (SMS OTP)' : 'None (Auto-Pass)'}
              </div>
            </div>
          </div>

          {/* Triggered Rules List */}
          {evalResult.triggered_rules && evalResult.triggered_rules.length > 0 ? (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Triggered Deterministic Security Rules ({evalResult.triggered_rules.length}):
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {evalResult.triggered_rules.map((rule, idx) => (
                  <span 
                    key={idx}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      color: '#f87171',
                      padding: '0.25rem 0.55rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontFamily: 'Consolas, monospace',
                    }}
                  >
                    {rule.rule_id} (weight: +{rule.weight})
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '0.75rem', color: '#34d399', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <CheckCircle2 size={13} />
              <span>Zero deterministic security rule violations triggered.</span>
            </div>
          )}

          {/* Challenge Button if Medium Risk */}
          {evalResult.status === 'PENDING_VERIFICATION' && evalResult.session_id && (
            <div style={{
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              borderRadius: '6px',
              padding: '0.85rem 1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Lock size={16} color="#fbbf24" />
                <div>
                  <div style={{ fontWeight: 600, color: '#fbbf24', fontSize: '0.85rem' }}>
                    Step-Up OTP Challenge Initiated
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    Session ID: <code>{evalResult.session_id.substring(0, 16)}...</code> • 180s TTL
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onOpenOtpModal(evalResult.session_id, evalResult.txn_id)}
                className="btn btn-warning"
              >
                <span>Solve OTP Challenge &rarr;</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
