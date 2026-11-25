import React, { useState } from 'react';
import {
  History,
  RefreshCw,
  Search,
  KeyRound,
  Download,
  Eye,
  Compass,
} from 'lucide-react';

export default function LiveTransactionFeed({
  transactions = [],
  loading,
  onRefresh,
  onOpenOtpModal,
  onSelectTxnForExplain,
  onInspectTxn,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [tierFilter, setTierFilter] = useState('ALL');

  const statusCounts = transactions.reduce(
    (acc, tx) => {
      acc.ALL += 1;
      if (tx.status && acc[tx.status] !== undefined) acc[tx.status] += 1;
      return acc;
    },
    { ALL: 0, APPROVED: 0, PENDING_VERIFICATION: 0, SECURITY_FLAGGED: 0, REJECTED: 0 }
  );

  const filtered = transactions.filter((tx) => {
    const tier = tx.risk_tier ?? tx.risk_assessment?.risk_tier ?? 'LOW';
    if (statusFilter !== 'ALL' && tx.status !== statusFilter) return false;
    if (tierFilter !== 'ALL' && tier !== tierFilter) return false;
    if (!searchTerm) return true;

    const term = searchTerm.toLowerCase();
    const vpa = (tx.recipient_vpa_masked || tx.recipient_vpa || '').toLowerCase();
    const user = (tx.user_hash || tx.user_id || '').toLowerCase();
    const status = (tx.status || '').toLowerCase();
    const txnId = (tx.txn_id || '').toLowerCase();
    return (
      txnId.includes(term) ||
      vpa.includes(term) ||
      user.includes(term) ||
      status.includes(term)
    );
  });

  const handleExportCsv = () => {
    const headers = ['Timestamp', 'Txn ID', 'User Hash', 'Amount INR', 'Recipient VPA', 'Composite Score', 'Risk Tier', 'Status', 'Latency (ms)'];
    const rows = filtered.map((tx) => {
      const score = tx.composite_score ?? tx.risk_assessment?.composite_score ?? 0;
      const tier = tx.risk_tier ?? tx.risk_assessment?.risk_tier ?? 'LOW';
      const latency = tx.latency_ms ?? tx.risk_assessment?.latency_ms ?? 0;
      return [
        tx.timestamp || tx.created_at || '',
        tx.txn_id || '',
        tx.user_hash || tx.user_id || '',
        (tx.amount ?? 0).toFixed(2),
        tx.recipient_vpa_masked || tx.recipient_vpa || '',
        score.toFixed(4),
        tier,
        tx.status || '',
        latency.toFixed(2),
      ].map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `fraud_shield_ledger_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const statusTabs = [
    { key: 'ALL', label: 'All' },
    { key: 'APPROVED', label: 'Approved' },
    { key: 'PENDING_VERIFICATION', label: 'Pending OTP' },
    { key: 'SECURITY_FLAGGED', label: 'Flagged' },
    { key: 'REJECTED', label: 'Rejected' },
  ];

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '0.85rem',
        }}
      >
        <div className="card-title" style={{ margin: 0 }}>
          <History size={18} color="#E85D3F" />
          <span>Real-Time Evaluated Micro-Transactions Stream</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{ position: 'relative', minWidth: '215px' }}>
            <Search
              size={14}
              color="#8C7F70"
              style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="text"
              placeholder="Search txn ID, VPA, status..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ fontSize: '0.75rem', padding: '0.38rem 0.65rem 0.38rem 2rem' }}
            />
          </div>

          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="form-select"
            style={{ width: 'auto', fontSize: '0.75rem', padding: '0.38rem 0.65rem' }}
          >
            <option value="ALL">All Tiers</option>
            <option value="LOW">Low Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="HIGH">High Risk</option>
          </select>

          <button
            onClick={handleExportCsv}
            disabled={filtered.length === 0}
            className="btn btn-outline btn-sm"
            title="Download visible ledger rows as CSV"
          >
            <Download size={12} color="#BE185D" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn btn-outline btn-sm"
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Status Filter Pills */}
      <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginBottom: '0.95rem' }}>
        {statusTabs.map((tab) => {
          const active = statusFilter === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatusFilter(tab.key)}
              className={`btn btn-sm ${active ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '0.28rem 0.65rem', fontSize: '0.72rem' }}
            >
              <span>{tab.label}</span>
              <span
                style={{
                  background: active ? 'rgba(255, 255, 255, 0.25)' : 'var(--bg-secondary)',
                  color: active ? '#FFFFFF' : 'var(--text-muted)',
                  padding: '0.05rem 0.4rem',
                  borderRadius: '999px',
                  fontSize: '0.66rem',
                }}
              >
                {statusCounts[tab.key] ?? 0}
              </span>
            </button>
          );
        })}
      </div>

      {/* Table Container */}
      <div className="table-container" style={{ maxHeight: '440px', overflowY: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Txn ID</th>
              <th>User (DPDP Hash)</th>
              <th>Amount (INR)</th>
              <th>Recipient VPA</th>
              <th>Score S(x)</th>
              <th>Tier</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length > 0 ? (
              filtered.map((tx) => {
                const score = tx.composite_score ?? tx.risk_assessment?.composite_score ?? 0;
                const tier = tx.risk_tier ?? tx.risk_assessment?.risk_tier ?? 'LOW';
                const latency = tx.latency_ms ?? tx.risk_assessment?.latency_ms ?? 0;
                const timeStr = tx.timestamp || tx.created_at;
                const recipientVpa = tx.recipient_vpa_masked || tx.recipient_vpa || 'N/A';
                const userDisplay = tx.user_hash || tx.user_id || 'masked';

                return (
                  <tr
                    key={tx.txn_id}
                    onClick={() => onInspectTxn?.(tx)}
                    style={{ cursor: onInspectTxn ? 'pointer' : 'default' }}
                    title="Click row to inspect details & analyst review"
                  >
                    <td style={{ color: 'var(--text-dim)', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {timeStr ? new Date(timeStr).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td>
                      <code style={{ fontSize: '0.75rem', color: 'var(--text-main)', fontWeight: 600 }}>
                        {tx.txn_id.substring(0, 8)}...
                      </code>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {userDisplay.substring(0, 10)}...
                      </code>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                      ₹{tx.amount?.toFixed(2)}
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {recipientVpa}
                    </td>
                    <td>
                      <span
                        className="mono"
                        style={{
                          fontWeight: 700,
                          color: tier === 'LOW' ? 'var(--tier-low)' : tier === 'MEDIUM' ? 'var(--tier-med)' : 'var(--tier-high)',
                        }}
                      >
                        {score.toFixed(4)}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          tier === 'LOW' ? 'badge-low' : tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                        }`}
                      >
                        {tier}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          tx.status === 'APPROVED'
                            ? 'badge-approved'
                            : tx.status === 'PENDING_VERIFICATION'
                            ? 'badge-pending'
                            : 'badge-rejected'
                        }`}
                      >
                        {tx.status}
                      </span>
                    </td>
                    <td
                      className="mono"
                      style={{ fontSize: '0.75rem', fontWeight: 600, color: latency < 50 ? 'var(--tier-low)' : 'var(--tier-high)', whiteSpace: 'nowrap' }}
                    >
                      {latency.toFixed(1)} ms
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        {tx.status === 'PENDING_VERIFICATION' && tx.session_id && (
                          <button
                            onClick={() => onOpenOtpModal(tx.session_id, tx.txn_id)}
                            className="btn btn-warning btn-sm"
                            style={{ padding: '0.22rem 0.5rem', fontSize: '0.7rem' }}
                            title="Verify Out-of-Band Step-Up OTP"
                          >
                            <KeyRound size={11} />
                            <span>OTP</span>
                          </button>
                        )}
                        <button
                          onClick={() => onInspectTxn?.(tx)}
                          className="btn btn-outline btn-sm"
                          style={{ padding: '0.22rem 0.5rem', fontSize: '0.7rem' }}
                          title="Inspect & Review Transaction"
                        >
                          <Eye size={11} />
                          <span>Review</span>
                        </button>
                        <button
                          onClick={() => onSelectTxnForExplain?.(tx.txn_id)}
                          className="btn btn-plum btn-sm"
                          style={{ padding: '0.22rem 0.5rem', fontSize: '0.7rem' }}
                          title="Inspect AI/ML & Rule Explainability Waterfall"
                        >
                          <Compass size={11} />
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
                  {loading ? 'Refreshing transaction stream...' : 'No transactions match the current filter.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div
        style={{
          marginTop: '0.8rem',
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem',
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
        }}
      >
        <span>Showing {filtered.length} of {transactions.length} loaded records</span>
        <span>Storage: SQLite 3 (WAL Mode) • Click any row for Analyst Review</span>
      </div>
    </div>
  );
}
