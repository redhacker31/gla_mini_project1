import React, { useState, useEffect } from 'react';
import { 
  X, 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  RefreshCw, 
  Hash, 
  Database,
  Lock,
  ArrowRight
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

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '820px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={20} color="#10b981" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#fff', fontWeight: 600 }}>
              Cryptographic Append-Only Audit Ledger
            </h3>
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
          {/* Verification Status Banner */}
          <div style={{
            background: verificationResult?.valid ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${verificationResult?.valid ? '#10b981' : '#ef4444'}`,
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '1rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {verificationResult?.valid ? (
                <ShieldCheck size={28} color="#10b981" />
              ) : (
                <ShieldAlert size={28} color="#ef4444" />
              )}
              <div>
                <div style={{ fontWeight: 700, color: verificationResult?.valid ? '#34d399' : '#f87171', fontSize: '0.95rem' }}>
                  {verificationResult?.valid 
                    ? 'Cryptographic Hash-Chain Integrity: VERIFIED INTACT' 
                    : 'Cryptographic Hash-Chain Integrity: INTEGRITY COMPROMISED'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Verified {verificationResult?.records_verified ?? 0} sequential audit blocks with zero data alteration.
                </div>
              </div>
            </div>

            <button
              onClick={() => { runVerification(); loadLogs(); }}
              disabled={verifying}
              className="btn btn-outline btn-sm"
            >
              <RefreshCw size={13} className={verifying ? 'spin' : ''} />
              <span>{verifying ? 'Verifying Chain...' : 'Re-verify Ledger'}</span>
            </button>
          </div>

          {/* SHA-256 Chaining Formula Explainer */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '0.85rem 1rem',
            borderRadius: '6px',
            border: '1px solid var(--border-color)',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            marginBottom: '1.25rem',
          }}>
            <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '0.25rem' }}>
              Sequential Merkle-Style Chaining Model:
            </div>
            <code>H_i = SHA256(H_{'i-1'} || entity_type || entity_id || action || payload || timestamp)</code>
            <div style={{ marginTop: '0.35rem', color: 'var(--text-dim)' }}>
              Any alteration to transaction history, risk scores, or OTP status cascades a cryptographic discrepancy detectable on linear scan.
            </div>
          </div>

          {/* Audit Logs Table */}
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
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
                      <td><code style={{ color: 'var(--accent-cyan)' }}>#{log.id}</code></td>
                      <td>
                        <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}>
                          {log.action}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.75rem' }}>{log.entity_type}</div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>
                          {log.entity_id?.substring(0, 12)}...
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{log.actor}</td>
                      <td>
                        <code style={{ fontSize: '0.7rem', color: '#34d399' }}>
                          {log.record_hash?.substring(0, 16)}...
                        </code>
                      </td>
                      <td style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>
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
