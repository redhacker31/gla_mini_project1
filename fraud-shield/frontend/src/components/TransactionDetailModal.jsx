import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  KeyRound,
  Compass,
  ShieldCheck,
  UserCheck,
  Ban,
} from 'lucide-react';
import { reviewTransaction } from '../services/api';

export default function TransactionDetailModal({
  transaction,
  onClose,
  onOpenOtpModal,
  onSelectTxnForExplain,
  onReviewed,
  onNotify,
}) {
  const [analystNote, setAnalystNote] = useState('');
  const [blacklistRecipient, setBlacklistRecipient] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!transaction) return null;

  const score = transaction.composite_score ?? transaction.risk_assessment?.composite_score ?? 0;
  const mlScore = transaction.ml_score ?? transaction.risk_assessment?.ml_score ?? 0;
  const tier = transaction.risk_tier ?? transaction.risk_assessment?.risk_tier ?? 'LOW';
  const latency = transaction.latency_ms ?? transaction.risk_assessment?.latency_ms ?? 0;
  const explanation = transaction.explanation ?? transaction.risk_assessment?.explanation ?? 'No explanation recorded.';
  const triggeredRules = transaction.triggered_rules || [];
  const canReview = ['PENDING_VERIFICATION', 'SECURITY_FLAGGED'].includes(transaction.status);

  const handleDecision = async (decision) => {
    setSubmitting(true);
    try {
      const resp = await reviewTransaction(
        transaction.txn_id,
        decision,
        analystNote,
        decision === 'REJECT' && blacklistRecipient
      );
      onNotify?.(
        resp.message || `Transaction ${decision === 'APPROVE' ? 'approved' : 'rejected'}.`,
        decision === 'APPROVE' ? 'success' : 'info'
      );
      if (resp.blacklisted_vpa) {
        onNotify?.(`Recipient VPA ${resp.blacklisted_vpa} added to live blacklist.`, 'info');
      }
      onReviewed?.();
      onClose?.();
    } catch (err) {
      onNotify?.(`Review submission failed: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const tierColor =
    tier === 'LOW' ? 'var(--tier-low)' : tier === 'MEDIUM' ? 'var(--tier-med)' : 'var(--tier-high)';

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="modal-content" style={{ maxWidth: '680px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            <ShieldCheck size={20} color={tierColor} />
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text-main)', fontWeight: 700 }}>
                Transaction Telemetry &amp; Analyst Review
              </h3>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                <code>{transaction.txn_id}</code>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-outline btn-sm"
            style={{ padding: '0.28rem' }}
          >
            <X size={17} />
          </button>
        </div>

        <div className="modal-body">
          {/* Top Summary Banner */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem',
              padding: '1.05rem',
              borderRadius: '10px',
              background: '#FAF8F5',
              border: `2px solid ${tierColor}`,
              marginBottom: '1.15rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Amount &amp; Destination</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-display)' }}>
                ₹{(transaction.amount ?? 0).toFixed(2)}{' '}
                <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  &rarr; {transaction.recipient_vpa_masked || transaction.recipient_vpa || 'N/A'}
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                Channel: <strong style={{ color: 'var(--text-main)' }}>{transaction.channel || 'UPI'}</strong> •{' '}
                DPDP ID: <code>{(transaction.user_hash || transaction.user_id || '').substring(0, 16)}...</code>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: tierColor, fontFamily: 'var(--font-display)' }}>
                S(x) = {score.toFixed(4)}
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
                <span
                  className={`badge ${
                    tier === 'LOW' ? 'badge-low' : tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                  }`}
                >
                  {tier} RISK
                </span>
                <span
                  className={`badge ${
                    transaction.status === 'APPROVED'
                      ? 'badge-approved'
                      : transaction.status === 'PENDING_VERIFICATION'
                      ? 'badge-pending'
                      : 'badge-rejected'
                  }`}
                >
                  {transaction.status}
                </span>
              </div>
            </div>
          </div>

          {/* Core Metrics Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.75rem',
              marginBottom: '1.15rem',
              fontSize: '0.8rem',
            }}
          >
            <div className="sub-panel" style={{ padding: '0.7rem 0.9rem' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontWeight: 600 }}>ML Anomaly Score (S_ml)</div>
              <div className="mono" style={{ fontWeight: 800, color: '#BE185D', fontSize: '1rem' }}>{mlScore.toFixed(4)}</div>
            </div>
            <div className="sub-panel" style={{ padding: '0.7rem 0.9rem' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontWeight: 600 }}>Evaluation Latency</div>
              <div className="mono" style={{ fontWeight: 800, color: latency < 50 ? 'var(--tier-low)' : 'var(--tier-high)', fontSize: '1rem' }}>
                {latency.toFixed(2)} ms
              </div>
            </div>
            <div className="sub-panel" style={{ padding: '0.7rem 0.9rem' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontWeight: 600 }}>Timestamp</div>
              <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.8rem', marginTop: '0.15rem' }}>
                {(transaction.timestamp || transaction.created_at)
                  ? new Date(transaction.timestamp || transaction.created_at).toLocaleString()
                  : 'Just now'}
              </div>
            </div>
          </div>

          {/* Decision Explanation */}
          <div
            className="sub-panel"
            style={{
              borderLeft: `4px solid ${tierColor}`,
              borderRadius: '0 8px 8px 0',
              padding: '0.8rem 1rem',
              fontSize: '0.8rem',
              marginBottom: '1.15rem',
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '0.2rem', color: 'var(--text-main)' }}>Risk Engine Decision Rationale</div>
            <div style={{ color: 'var(--text-muted)' }}>{explanation}</div>
          </div>

          {/* Triggered Rules */}
          <div style={{ marginBottom: '1.15rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.45rem', textTransform: 'uppercase' }}>
              Triggered Deterministic Rules ({triggeredRules.length})
            </div>
            {triggeredRules.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                {triggeredRules.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.55rem 0.8rem',
                      background: 'var(--tier-high-bg)',
                      border: '1px solid var(--tier-high-border)',
                      borderRadius: '8px',
                      fontSize: '0.76rem',
                    }}
                  >
                    <div>
                      <code style={{ color: 'var(--tier-high)', fontWeight: 700 }}>{r.rule_id}</code>
                      <div style={{ color: 'var(--text-muted)', marginTop: '0.12rem' }}>{r.reason}</div>
                    </div>
                    <span className="badge badge-high mono" style={{ whiteSpace: 'nowrap' }}>
                      +{(r.penalty ?? r.weight ?? 0).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.78rem', color: 'var(--tier-low)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle2 size={14} />
                <span>No deterministic security rules triggered.</span>
              </div>
            )}
          </div>

          {/* Analyst Override Panel */}
          {canReview && (
            <div className="sub-panel" style={{ padding: '1rem' }}>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={15} color="#E85D3F" />
                <span>Fraud Analyst Manual Review &amp; Resolution</span>
              </div>

              <div className="form-group" style={{ marginBottom: '0.7rem' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Optional audit note (e.g. Verified with customer via callback / Confirmed mule)"
                  value={analystNote}
                  onChange={(e) => setAnalystNote(e.target.value)}
                  maxLength={200}
                />
              </div>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  marginBottom: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={blacklistRecipient}
                  onChange={(e) => setBlacklistRecipient(e.target.checked)}
                />
                <span>When rejecting, also register unmasked recipient VPA to live Fraud Blacklist</span>
              </label>

              <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('APPROVE')}
                  className="btn btn-success btn-sm"
                >
                  <CheckCircle2 size={14} />
                  <span>Approve (False Positive)</span>
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision('REJECT')}
                  className="btn btn-danger btn-sm"
                >
                  <Ban size={14} />
                  <span>Confirm Fraud &amp; Reject</span>
                </button>
                {transaction.status === 'PENDING_VERIFICATION' && transaction.session_id && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose?.();
                      onOpenOtpModal?.(transaction.session_id, transaction.txn_id);
                    }}
                    className="btn btn-warning btn-sm"
                    style={{ marginLeft: 'auto' }}
                  >
                    <KeyRound size={14} />
                    <span>Solve Customer OTP</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <button
            type="button"
            onClick={() => {
              onClose?.();
              onSelectTxnForExplain?.(transaction.txn_id);
            }}
            className="btn btn-primary btn-sm"
          >
            <Compass size={14} />
            <span>Open in Explainability Lab</span>
          </button>

          <button type="button" onClick={onClose} className="btn btn-outline btn-sm">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
