import React, { useState } from 'react';
import {
  Send,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Zap,
  Lock,
  Smartphone,
  Compass,
  CreditCard,
} from 'lucide-react';
import { evaluateTransaction } from '../services/api';

export default function TransactionEvaluator({
  thresholds = { low: 0.45, high: 0.80 },
  onTransactionEvaluated,
  onOpenOtpModal,
  onInspectInExplainability,
  onNotify,
}) {
  const [formData, setFormData] = useState({
    user_id: 'user_ramesh_rural_01',
    amount: '150.00',
    recipient_vpa: 'local_kirana@paytm',
    merchant_category: 'grocery',
    channel: 'QR_SCAN',
    device_id: 'dev_android_102',
  });

  const [autoOpenOtp, setAutoOpenOtp] = useState(true);
  const [loading, setLoading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);

  const lowThresh = thresholds?.low ?? 0.45;
  const highThresh = thresholds?.high ?? 0.80;

  const applyPreset = (preset) => {
    if (preset === 'tea') {
      setFormData({
        user_id: 'user_priya_teacher_02',
        amount: '35.00',
        recipient_vpa: 'chai.corner@okaxis',
        merchant_category: 'food',
        channel: 'QR_SCAN',
        device_id: 'dev_android_204',
      });
    } else if (preset === 'routine') {
      setFormData({
        user_id: 'user_ramesh_rural_01',
        amount: '120.00',
        recipient_vpa: 'local_kirana@paytm',
        merchant_category: 'grocery',
        channel: 'QR_SCAN',
        device_id: 'dev_android_102',
      });
    } else if (preset === 'velocity') {
      setFormData({
        user_id: `usr_burst_${Math.floor(Math.random() * 900 + 100)}`,
        amount: '480.00',
        recipient_vpa: 'suspicious_mule_01@ybl',
        merchant_category: 'p2p',
        channel: 'UPI_APP',
        device_id: 'dev_unknown_999',
      });
    } else if (preset === 'smurfing') {
      setFormData({
        user_id: 'user_smurf_syndicate',
        amount: '990.00',
        recipient_vpa: 'layering_aggregator@icici',
        merchant_category: 'p2p',
        channel: 'P2P_INTENT',
        device_id: 'dev_emulator_v3',
      });
    } else if (preset === 'blacklist') {
      setFormData({
        user_id: 'user_targeted_victim',
        amount: '350.00',
        recipient_vpa: 'blacklisted_mule99@upi',
        merchant_category: 'miscellaneous',
        channel: 'COLLECT_REQUEST',
        device_id: 'dev_android_456',
      });
    }
  };

  const handleEvaluationResponse = (response) => {
    setEvalResult(response);
    onTransactionEvaluated?.(response);

    if (response.status === 'APPROVED') {
      onNotify?.(`Approved ₹${response.amount.toFixed(2)} in ${response.latency_ms.toFixed(1)}ms`, 'success');
    } else if (response.status === 'PENDING_VERIFICATION') {
      onNotify?.(`Step-Up OTP Challenge triggered (S=${response.composite_score.toFixed(3)})`, 'info');
      if (autoOpenOtp && response.session_id) {
        onOpenOtpModal?.(response.session_id, response.txn_id);
      }
    } else {
      onNotify?.(`Blocked High-Risk Transfer (S=${response.composite_score.toFixed(3)})`, 'error');
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
      handleEvaluationResponse(response);
    } catch (err) {
      onNotify?.(`Evaluation failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRapidBurst = async () => {
    setLoading(true);
    setEvalResult(null);
    try {
      const payload = {
        user_id: formData.user_id,
        amount: parseFloat(formData.amount),
        recipient_id: formData.recipient_vpa,
        recipient_vpa: formData.recipient_vpa,
        merchant_category: formData.merchant_category,
        channel: formData.channel,
        device_id: formData.device_id,
      };
      let lastResp = null;
      for (let i = 0; i < 3; i++) {
        lastResp = await evaluateTransaction(payload);
        onTransactionEvaluated?.(lastResp);
        if (i < 2) await new Promise((r) => setTimeout(r, 60));
      }
      if (lastResp) {
        handleEvaluationResponse(lastResp);
      }
    } catch (err) {
      onNotify?.(`Burst failed: ${err.message}`, 'error');
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
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
      {/* LEFT PANE: Interactive Mobile UPI Checkout Prototype */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div className="card-title" style={{ margin: 0 }}>
            <Smartphone size={18} color="var(--accent-cyan)" />
            <span>UPI Micro-Payment Checkout Simulator</span>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.73rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoOpenOtp}
              onChange={(e) => setAutoOpenOtp(e.target.checked)}
            />
            <span>Auto-open OTP prompt</span>
          </label>
        </div>

        {/* Quick Presets Ribbon */}
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginBottom: '1.1rem' }}>
          <button type="button" onClick={() => applyPreset('tea')} className="btn btn-outline btn-sm">
            ☕ Tea Stall (₹35)
          </button>
          <button type="button" onClick={() => applyPreset('routine')} className="btn btn-outline btn-sm">
            🛒 Kirana Store (₹120)
          </button>
          <button type="button" onClick={() => applyPreset('velocity')} className="btn btn-outline btn-sm">
            ⚡ Velocity Test (₹480)
          </button>
          <button type="button" onClick={() => applyPreset('smurfing')} className="btn btn-outline btn-sm">
            🌊 Smurfing (₹990)
          </button>
          <button type="button" onClick={() => applyPreset('blacklist')} className="btn btn-outline btn-sm">
            🚫 Blacklisted Mule (₹350)
          </button>
        </div>

        {/* Payment Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
            <div className="form-group">
              <label className="form-label">Payer User ID</label>
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
              <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.35rem' }}>
                {['45.00', '120.00', '480.00', '950.00'].map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    onClick={() => setFormData({ ...formData, amount: amt })}
                    className="btn btn-outline btn-sm"
                    style={{ padding: '0.12rem 0.4rem', fontSize: '0.68rem' }}
                  >
                    ₹{parseInt(amt, 10)}
                  </button>
                ))}
              </div>
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
                <option value="grocery">Grocery &amp; Supermarket</option>
                <option value="food">Food &amp; Tea Stall</option>
                <option value="utilities">Utilities &amp; Recharges</option>
                <option value="transport">Local Transport / Auto</option>
                <option value="p2p">Peer-to-Peer (P2P)</option>
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
                <option value="QR_SCAN">UPI Dynamic / Static QR</option>
                <option value="UPI_APP">UPI App Transfer</option>
                <option value="P2P_INTENT">P2P Intent Link</option>
                <option value="COLLECT_REQUEST">Collect Request</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Device Fingerprint</label>
              <input
                type="text"
                className="form-input"
                value={formData.device_id}
                onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.65rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              disabled={loading}
              onClick={handleRapidBurst}
              className="btn btn-outline"
              title="Fire 3 micro-transactions in rapid succession (<1s) to trigger sliding-window velocity detection"
            >
              <Zap size={14} color="#f59e0b" />
              <span>Fire Rapid Burst (x3)</span>
            </button>

            <button type="submit" disabled={loading} className="btn btn-primary" style={{ flex: 1 }}>
              {loading ? <Zap size={14} className="spin" /> : <Send size={14} />}
              <span>{loading ? 'Evaluating Gateway...' : `Pay ₹${parseFloat(formData.amount || 0).toFixed(2)} via Fraud Shield`}</span>
            </button>
          </div>
        </form>
      </div>

      {/* RIGHT PANE: Real-Time Gateway Response & Receipt */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div className="card-title" style={{ margin: 0 }}>
            <CreditCard size={18} color="var(--accent-cyan)" />
            <span>Gateway Risk Verdict &amp; Telemetry</span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>SLA Target &lt; 50ms</span>
        </div>

        {evalResult ? (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.9)',
              borderRadius: '8px',
              border: `1px solid ${getTierColor(evalResult.risk_tier)}`,
              padding: '1.15rem',
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                gap: '0.75rem',
                borderBottom: '1px solid var(--border-color)',
                paddingBottom: '0.85rem',
                marginBottom: '0.9rem',
              }}
            >
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Txn: <code style={{ color: '#fff' }}>{evalResult.txn_id.substring(0, 14)}...</code>
                </div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                  ₹{evalResult.amount?.toFixed(2)} &rarr; {evalResult.recipient_vpa_masked || evalResult.recipient_vpa}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                  DPDP Salted Hash: <code>{(evalResult.user_hash || evalResult.user_id)?.substring(0, 14)}...</code>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Composite Score S(x)</div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: getTierColor(evalResult.risk_tier) }}>
                  {evalResult.composite_score?.toFixed(4)}
                </div>
                <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                  <span
                    className={`badge ${
                      evalResult.risk_tier === 'LOW' ? 'badge-low' : evalResult.risk_tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                    }`}
                  >
                    {evalResult.risk_tier}
                  </span>
                  <span
                    className={`badge ${
                      evalResult.status === 'APPROVED'
                        ? 'badge-approved'
                        : evalResult.status === 'PENDING_VERIFICATION'
                        ? 'badge-pending'
                        : 'badge-rejected'
                    }`}
                  >
                    {evalResult.status}
                  </span>
                </div>
              </div>
            </div>

            {/* Score Gauge */}
            <div style={{ marginBottom: '0.9rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                <span>Low (&lt; {lowThresh.toFixed(2)})</span>
                <span>OTP ({lowThresh.toFixed(2)} - {highThresh.toFixed(2)})</span>
                <span>Block (&ge; {highThresh.toFixed(2)})</span>
              </div>
              <div style={{ height: '8px', borderRadius: '4px', background: '#1e293b', overflow: 'hidden', position: 'relative' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${Math.min(100, Math.max(0, evalResult.composite_score * 100))}%`,
                    background: getTierColor(evalResult.risk_tier),
                    borderRadius: '4px',
                    transition: 'width 0.35s ease',
                  }}
                />
              </div>
            </div>

            {/* Sub-Metrics */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.6rem',
                background: 'rgba(0, 0, 0, 0.25)',
                padding: '0.65rem',
                borderRadius: '6px',
                fontSize: '0.78rem',
                marginBottom: '0.9rem',
              }}
            >
              <div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>Isolation Forest</div>
                <div style={{ fontWeight: 700, color: '#38bdf8' }}>{evalResult.ml_score?.toFixed(4)}</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>Latency</div>
                <div style={{ fontWeight: 700, color: evalResult.latency_ms < 50 ? '#34d399' : '#f87171' }}>
                  {evalResult.latency_ms?.toFixed(2)} ms
                </div>
              </div>
              <div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>Challenge</div>
                <div style={{ fontWeight: 700, color: evalResult.challenge_required ? '#fbbf24' : '#10b981' }}>
                  {evalResult.challenge_required ? 'SMS OTP' : 'None'}
                </div>
              </div>
            </div>

            {/* Explanation */}
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.85rem', lineHeight: 1.45 }}>
              {evalResult.explanation}
            </div>

            {/* Triggered Rules */}
            {evalResult.triggered_rules && evalResult.triggered_rules.length > 0 && (
              <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginBottom: '0.9rem' }}>
                {evalResult.triggered_rules.map((rule, idx) => (
                  <span
                    key={idx}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.35)',
                      color: '#f87171',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontFamily: 'Consolas, monospace',
                    }}
                  >
                    {rule.rule_id} (+{(rule.penalty ?? rule.weight ?? 0).toFixed(2)})
                  </span>
                ))}
              </div>
            )}

            {/* Action Bar */}
            <div style={{ marginTop: 'auto', display: 'flex', gap: '0.6rem', flexWrap: 'wrap', paddingTop: '0.5rem' }}>
              {evalResult.status === 'PENDING_VERIFICATION' && evalResult.session_id && (
                <button
                  type="button"
                  onClick={() => onOpenOtpModal?.(evalResult.session_id, evalResult.txn_id)}
                  className="btn btn-warning btn-sm"
                  style={{ flex: 1 }}
                >
                  <Lock size={14} />
                  <span>Solve Step-Up OTP Challenge</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => onInspectInExplainability?.(evalResult.txn_id)}
                className="btn btn-outline btn-sm"
              >
                <Compass size={14} />
                <span>Inspect Explainability &rarr;</span>
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '2rem 1rem',
              background: 'rgba(15, 23, 42, 0.45)',
              borderRadius: '8px',
              border: '1px dashed var(--border-light)',
              color: 'var(--text-dim)',
              fontSize: '0.82rem',
            }}
          >
            <Zap size={32} color="var(--accent-cyan)" style={{ opacity: 0.7, marginBottom: '0.75rem' }} />
            <div style={{ color: '#fff', fontWeight: 600, marginBottom: '0.35rem' }}>
              Ready to Score Real-Time Micro-Transactions
            </div>
            <p style={{ maxWidth: '340px', lineHeight: 1.5 }}>
              Select a scenario preset or submit a custom UPI transfer on the left to observe sub-50ms Isolation Forest inference, deterministic rules, and adaptive Step-Up OTP challenges.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
