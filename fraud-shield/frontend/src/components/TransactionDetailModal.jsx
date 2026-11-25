import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  ShieldAlert,
  AlertTriangle,
  KeyRound,
  Compass,
  Clock,
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
      onNotify?.(resp.message || `Transaction ${decision === 'APPROVE' ? 'approved' : 'rejected'}.`, decision === 'APPROVE' ? 'success' : 'info');
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
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#fff', fontWeight: 600 }}>
                Transaction Telemetry & Analyst Review
              </h3>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                <code>{transaction.txn_id}</code>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-outline btn-sm"
            style={{ border: 'none', padding: '0.25rem' }}
          >
            <X size={18} />
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
              padding: '1rem',
              borderRadius: '8px',
              background: 'rgba(15, 23, 42, 0.8)',
              border: `1px solid ${tierColor}`,
              marginBottom: '1.15rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Amount & Destination</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff' }}>
                ₹{(transaction.amount ?? 0).toFixed(2)}{' '}
                <span style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-muted)' }}>
                  &rarr; {transaction.recipient_vpa_masked || transaction.recipient_vpa || 'N/A'}
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                Channel: <strong style={{ color: '#cbd5e1' }}>{transaction.channel || 'UPI'}</strong> •{' '}
                DPDP ID: <code>{(transaction.user_hash || transaction.user_id || '').substring(0, 16)}...</code>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: tierColor }}>
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
            <div style={{ background: 'rgba(15, 23, 42, 0.55)', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>ML Anomaly Score (S_ml)</div>
              <div style={{ fontWeight: 700, color: '#38bdf8', fontSize: '1rem' }}>{mlScore.toFixed(4)}</div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.55)', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Evaluation Latency</div>
              <div style={{ fontWeight: 700, color: latency < 50 ? '#34d399' : '#f87171', fontSize: '1rem' }}>
                {latency.toFixed(2)} ms
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.55)', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Timestamp</div>
              <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.82rem', marginTop: '0.15rem' }}>
                {(transaction.timestamp || transaction.created_at)
                  ? new Date(transaction.timestamp || transaction.created_at).toLocaleString()
                  : 'Just now'}
              </div>
            </div>
          </div>

          {/* Decision Explanation */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.55)',
              borderLeft: `3px solid ${tierColor}`,
              padding: '0.75rem 1rem',
              borderRadius: '0 6px 6px 0',
              fontSize: '0.8rem',
              color: 'var(--text-main)',
              marginBottom: '1.15rem',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '0.2rem', color: '#fff' }}>Risk Engine Decision Rationale</div>
            <div style={{ color: 'var(--text-muted)' }}>{explanation}</div>
          </div>

          {/* Triggered Rules */}
          <div style={{ marginBottom: '1.15rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.45rem' }}>
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
                      padding: '0.5rem 0.75rem',
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                    }}
                  >
                    <div>
                      <code style={{ color: '#f87171', fontWeight: 700 }}>{r.rule_id}</code>
                      <div style={{ color: 'var(--text-muted)', marginTop: '0.1rem' }}>{r.reason}</div>
                    </div>
                    <span className="badge badge-high" style={{ whiteSpace: 'nowrap' }}>
                      +{(r.penalty ?? r.weight ?? 0).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.78rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle2 size={14} />
                <span>No deterministic security rules triggered.</span>
              </div>
            )}
          </div>

          {/* Analyst Override Panel for Pending / Flagged Transactions */}
          {canReview && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.75)',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                padding: '1rem',
              }}
            >
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fff', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={15} color="var(--accent-cyan)" />
                <span>Fraud Analyst Manual Review & Resolution</span>
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
                  <span>Confirm Fraud & Reject</span>
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
