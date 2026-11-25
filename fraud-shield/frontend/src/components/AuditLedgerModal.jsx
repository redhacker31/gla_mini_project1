import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
} from 'lucide-react';
import { verifyAuditLedger, fetchAuditLogs } from '../services/api';

export default function AuditLedgerModal({ onClose, onNotify }) {
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(true);

  const runVerification = async () => {
    setVerifying(true);
    try {
      const resp = await verifyAuditLedger();
      setVerificationResult(resp.audit_verification);
      if (resp.audit_verification?.valid) {
        onNotify?.('Audit hash chain cryptographically verified: 100% intact.', 'success');
      } else {
        onNotify?.('Audit chain verification failed: potential tampering detected!', 'error');
      }
    } catch (err) {
      onNotify?.(`Audit verification error: ${err.message}`, 'error');
    } finally {
      setVerifying(false);
    }
  };

  const loadLogs = async () => {
    setLoadingLogs(true);
    try {
      const resp = await fetchAuditLogs(30);
      if (resp.data) {
        setAuditLogs(resp.data);
      }
    } catch (err) {
      console.warn('Failed to load audit logs:', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    runVerification();
    loadLogs();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="modal-content" style={{ maxWidth: '820px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            <ShieldCheck size={20} color="#059669" />
            <h3 style={{ margin: 0, fontSize: '1.08rem', color: 'var(--text-main)', fontWeight: 700 }}>
              Cryptographic Append-Only Audit Ledger
            </h3>
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
          {/* Verification Status Banner */}
          <div
            style={{
              background: verificationResult?.valid ? 'var(--tier-low-bg)' : 'var(--tier-high-bg)',
              border: `1px solid ${verificationResult?.valid ? 'var(--tier-low-border)' : 'var(--tier-high-border)'}`,
              borderRadius: '10px',
              padding: '1rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {verificationResult?.valid ? (
                <ShieldCheck size={28} color="#059669" />
              ) : (
                <ShieldAlert size={28} color="#DC2626" />
              )}
              <div>
                <div style={{ fontWeight: 700, color: verificationResult?.valid ? 'var(--tier-low)' : 'var(--tier-high)', fontSize: '0.95rem' }}>
                  {verificationResult?.valid
                    ? 'Cryptographic Hash-Chain Integrity: VERIFIED INTACT'
                    : verifying
                    ? 'Verifying Sequential Hash Chain...'
                    : 'Cryptographic Hash-Chain Integrity: INTEGRITY COMPROMISED'}
                </div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Verified {verificationResult?.total_records ?? verificationResult?.records_verified ?? 0} sequential audit blocks with zero data alteration.
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                runVerification();
                loadLogs();
              }}
              disabled={verifying}
              className="btn btn-outline btn-sm"
            >
              <RefreshCw size={13} className={verifying ? 'spin' : ''} />
              <span>{verifying ? 'Verifying Chain...' : 'Re-verify Ledger'}</span>
            </button>
          </div>

          {/* SHA-256 Chaining Formula Explainer */}
          <div className="sub-panel" style={{ padding: '0.9rem 1rem', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            <div style={{ color: '#9D174D', fontWeight: 700, marginBottom: '0.3rem' }}>
              Sequential Merkle-Style Chaining Model:
            </div>
            <code style={{ color: 'var(--text-main)', fontWeight: 600 }}>
              H_i = SHA256(H_{'i-1'} || entity_type || entity_id || action || payload || timestamp)
            </code>
            <div style={{ marginTop: '0.35rem', color: 'var(--text-dim)' }}>
              Any alteration to transaction history, risk scores, or OTP status cascades a cryptographic discrepancy detectable on linear scan.
            </div>
          </div>

          {/* Audit Logs Table */}
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.55rem', textTransform: 'uppercase' }}>
            Recent Tamper-Evident Audit Records ({auditLogs.length}):
          </div>

          <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Block</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Actor</th>
                  <th>Record SHA-256 Hash</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.length > 0 ? (
                  auditLogs.map((log) => (
                    <tr key={log.id}>
                      <td><code style={{ color: '#E85D3F', fontWeight: 700 }}>#{log.id}</code></td>
                      <td>
                        <span className="badge badge-plum">
                          {log.action}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-main)' }}>{log.entity_type}</div>
                        <div className="mono" style={{ fontSize: '0.66rem', color: 'var(--text-dim)' }}>
                          {log.entity_id?.substring(0, 14)}...
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 500 }}>{log.actor}</td>
                      <td>
                        <code style={{ fontSize: '0.72rem', color: 'var(--tier-low)', fontWeight: 600 }}>
                          {log.record_hash?.substring(0, 16)}...
                        </code>
                      </td>
                      <td style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'N/A'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '1.5rem' }}>
                      {loadingLogs ? 'Loading ledger blocks...' : 'No audit entries recorded yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-outline btn-sm">
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
}
