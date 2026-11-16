import React, { useState } from 'react';
import { 
  History, 
  RefreshCw, 
  Search, 
  ExternalLink, 
  KeyRound, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert,
  ArrowUpDown
} from 'lucide-react';

export default function LiveTransactionFeed({ 
  transactions, 
  loading, 
  onRefresh, 
  onOpenOtpModal,
  onSelectTxnForExplain
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = transactions.filter((tx) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (tx.txn_id && tx.txn_id.toLowerCase().includes(term)) ||
      (tx.recipient_vpa_masked && tx.recipient_vpa_masked.toLowerCase().includes(term)) ||
      (tx.user_hash && tx.user_hash.toLowerCase().includes(term)) ||
      (tx.status && tx.status.toLowerCase().includes(term))
    );
  });

  return (
    <div className="card">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1rem',
      }}>
        <div className="card-title" style={{ margin: 0 }}>
          <History size={18} color="var(--accent-cyan)" />
          <span>Real-Time Evaluated Micro-Transactions Stream</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{ position: 'relative', minWidth: '220px' }}>
            <Search 
              size={14} 
              color="var(--text-dim)" 
              style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }} 
            />
            <input
              type="text"
              placeholder="Filter by txn ID, VPA, status..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '2rem', fontSize: '0.75rem', padding: '0.35rem 0.65rem 0.35rem 2rem' }}
            />
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn btn-outline btn-sm"
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            <span>Refresh Feed</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="table-container" style={{ maxHeight: '420px', overflowY: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Txn ID</th>
              <th>User (DPDP Hash)</th>
              <th>Amount (INR)</th>
              <th>Recipient VPA</th>
              <th>Composite Score S(x)</th>
              <th>Risk Tier</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length > 0 ? (
              filtered.map((tx) => {
                const score = tx.risk_assessment?.composite_score ?? 0;
                const tier = tx.risk_assessment?.risk_tier ?? 'LOW';
                const latency = tx.risk_assessment?.latency_ms ?? 0;

                return (
                  <tr key={tx.txn_id}>
                    <td style={{ color: 'var(--text-dim)', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {tx.created_at ? new Date(tx.created_at).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td>
                      <code style={{ fontSize: '0.75rem', color: '#fff' }}>
                        {tx.txn_id.substring(0, 8)}...
                      </code>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                        {tx.user_hash ? tx.user_hash.substring(0, 10) + '...' : 'masked'}
                      </code>
                    </td>
                    <td style={{ fontWeight: 700, color: '#fff' }}>
                      ₹{tx.amount?.toFixed(2)}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {tx.recipient_vpa_masked || 'N/A'}
                    </td>
                    <td>
                      <span style={{
                        fontWeight: 700,
                        fontFamily: 'Consolas, monospace',
                        color: tier === 'LOW' ? 'var(--tier-low)' : tier === 'MEDIUM' ? 'var(--tier-med)' : 'var(--tier-high)',
                      }}>
                        {score.toFixed(4)}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${
                        tier === 'LOW' ? 'badge-low' : tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                      }`}>
                        {tier}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${
                        tx.status === 'APPROVED' ? 'badge-approved' :
                        tx.status === 'PENDING_VERIFICATION' ? 'badge-pending' : 'badge-rejected'
                      }`}>
                        {tx.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.75rem', color: latency < 50 ? '#34d399' : '#f87171' }}>
                      {latency.toFixed(1)} ms
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        {tx.status === 'PENDING_VERIFICATION' && tx.session_id && (
                          <button
                            onClick={() => onOpenOtpModal(tx.session_id, tx.txn_id)}
                            className="btn btn-warning btn-sm"
                            style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem' }}
                            title="Verify Out-of-Band Step-Up OTP"
                          >
                            <KeyRound size={11} />
                            <span>OTP</span>
                          </button>
                        )}
                        <button
                          onClick={() => onSelectTxnForExplain?.(tx.txn_id)}
                          className="btn btn-outline btn-sm"
                          style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem' }}
                          title="Inspect AI/ML & Rule Explainability Waterfall"
                        >
                          <span>Explain</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' }}>
                  {loading ? 'Refreshing transaction stream...' : 'No transactions matching query.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{
        marginTop: '0.75rem',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: 'var(--text-dim)',
      }}>
        <span>Showing {filtered.length} of {transactions.length} records</span>
        <span>Storage: SQLite 3 with Write-Ahead Logging (WAL)</span>
      </div>
    </div>
  );
}
