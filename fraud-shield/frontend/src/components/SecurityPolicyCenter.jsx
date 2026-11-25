import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Key,
  Sliders,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileCode,
  Send,
} from 'lucide-react';
import {
  fetchSecurityStatus,
  fetchBlacklistAndPolicy,
  addBlacklistVpa,
  removeBlacklistVpa,
  updateRiskThresholds,
  generateHmacSignature,
  verifyHmacSignature,
} from '../services/api';

export default function SecurityPolicyCenter({ onPolicyUpdated, onNotify }) {
  const [posture, setPosture] = useState(null);
  const [blacklist, setBlacklist] = useState([]);
  const [newVpa, setNewVpa] = useState('');
  const [newReason, setNewReason] = useState('');
  const [threshLow, setThreshLow] = useState(0.45);
  const [threshHigh, setThreshHigh] = useState(0.80);
  const [loadingPolicy, setLoadingPolicy] = useState(false);

  // HMAC Sandbox state
  const [hmacPayloadText, setHmacPayloadText] = useState(
    JSON.stringify({ user_id: 'usr_gateway_client_01', amount: 250.0, recipient_vpa: 'kirana@paytm' }, null, 2)
  );
  const [hmacResult, setHmacResult] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [hmacBusy, setHmacBusy] = useState(false);

  const loadAll = useCallback(async () => {
    setLoadingPolicy(true);
    try {
      const [secData, blData] = await Promise.all([
        fetchSecurityStatus(),
        fetchBlacklistAndPolicy(),
      ]);
      if (secData) setPosture(secData);
      if (blData) {
        setBlacklist(blData.blacklist || []);
        if (blData.thresholds) {
          setThreshLow(blData.thresholds.low ?? 0.45);
          setThreshHigh(blData.thresholds.high ?? 0.80);
        }
      }
    } catch (err) {
      onNotify?.(`Failed to load security policy: ${err.message}`, 'error');
    } finally {
      setLoadingPolicy(false);
    }
  }, [onNotify]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleAddBlacklist = async (e) => {
    e.preventDefault();
    if (!newVpa.trim()) return;
    try {
      const resp = await addBlacklistVpa(newVpa.trim(), newReason.trim() || 'Added via Security Console');
      setBlacklist(resp.blacklist || []);
      setNewVpa('');
      setNewReason('');
      onNotify?.(
        resp.added ? `Added ${resp.vpa} to active blacklist.` : `${resp.vpa} is already blacklisted.`,
        'success'
      );
      onPolicyUpdated?.();
    } catch (err) {
      onNotify?.(`Could not blacklist VPA: ${err.message}`, 'error');
    }
  };

  const handleRemoveBlacklist = async (vpa) => {
    try {
      const resp = await removeBlacklistVpa(vpa);
      setBlacklist(resp.blacklist || []);
      onNotify?.(`Removed ${vpa} from blacklist.`, 'info');
      onPolicyUpdated?.();
    } catch (err) {
      onNotify?.(`Could not remove VPA: ${err.message}`, 'error');
    }
  };

  const handleApplyThresholds = async (lowVal = threshLow, highVal = threshHigh) => {
    try {
      const resp = await updateRiskThresholds(lowVal, highVal);
      setThreshLow(resp.thresholds.low);
      setThreshHigh(resp.thresholds.high);
      onNotify?.(
        `Updated live risk thresholds: LOW < ${resp.thresholds.low}, HIGH >= ${resp.thresholds.high}`,
        'success'
      );
      onPolicyUpdated?.();
    } catch (err) {
      onNotify?.(`Threshold update failed: ${err.message}`, 'error');
    }
  };

  const handleSignPayload = async () => {
    setHmacBusy(true);
    setVerifyResult(null);
    try {
      const parsed = JSON.parse(hmacPayloadText);
      const signed = await generateHmacSignature(parsed);
      setHmacResult(signed);
      onNotify?.('Generated valid HMAC-SHA256 gateway signature.', 'info');
    } catch (err) {
      onNotify?.(`Invalid JSON or signing failed: ${err.message}`, 'error');
    } finally {
      setHmacBusy(false);
    }
  };

  const handleVerifyPayload = async () => {
    if (!hmacResult) {
      onNotify?.('Generate a signature first.', 'error');
      return;
    }
    setHmacBusy(true);
    try {
      const parsed = JSON.parse(hmacPayloadText);
      const resp = await verifyHmacSignature(parsed, hmacResult.signature, hmacResult.timestamp);
      setVerifyResult({ ok: true, data: resp });
      onNotify?.('HMAC-SHA256 signature & anti-replay check PASSED!', 'success');
    } catch (err) {
      setVerifyResult({ ok: false, error: err.message });
      onNotify?.(`Gateway verification rejected: ${err.message}`, 'error');
    } finally {
      setHmacBusy(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Grid: Blacklist Manager + Risk Threshold Tuner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {/* 1. Live Blacklist Manager */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
            <div className="card-title" style={{ margin: 0 }}>
              <ShieldAlert size={18} color="#ef4444" />
              <span>Live Threat Blacklist VPA Manager</span>
            </div>
            <span className="badge badge-high">{blacklist.length} Blocked VPAs</span>
          </div>

          <p className="card-desc" style={{ marginBottom: '1rem' }}>
            Any transaction targeting these VPAs immediately triggers <code>RULE_BLACKLISTED_RECIPIENT</code> (+2.50 penalty) and freezes the transfer in sub-50ms.
          </p>

          <form onSubmit={handleAddBlacklist} style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. cyber_mule_07@ybl"
                value={newVpa}
                onChange={(e) => setNewVpa(e.target.value)}
                required
              />
              <button type="submit" className="btn btn-danger btn-sm" style={{ whiteSpace: 'nowrap' }}>
                <Plus size={14} />
                <span>Blacklist VPA</span>
              </button>
            </div>
            <input
              type="text"
              className="form-input"
              placeholder="Optional threat intel note (e.g. Reported phishing QR handle)"
              value={newReason}
              onChange={(e) => setNewReason(e.target.value)}
              style={{ fontSize: '0.78rem', padding: '0.4rem 0.65rem' }}
            />
          </form>

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.45rem',
              maxHeight: '210px',
              overflowY: 'auto',
              padding: '0.75rem',
              background: 'rgba(15, 23, 42, 0.55)',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}
          >
            {blacklist.length > 0 ? (
              blacklist.map((vpa) => (
                <div
                  key={vpa}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.45rem',
                    padding: '0.3rem 0.6rem',
                    background: 'rgba(239, 68, 68, 0.14)',
                    border: '1px solid rgba(239, 68, 68, 0.35)',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    color: '#fca5a5',
                  }}
                >
                  <code>{vpa}</code>
                  <button
                    type="button"
                    onClick={() => handleRemoveBlacklist(vpa)}
                    title={`Remove ${vpa} from blacklist`}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#f87171',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      padding: 0,
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            ) : (
              <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>No VPAs currently blacklisted.</span>
            )}
          </div>
        </div>

        {/* 2. Adaptive Risk Threshold Policy Tuner */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
            <div className="card-title" style={{ margin: 0 }}>
              <Sliders size={18} color="var(--accent-cyan)" />
              <span>3-Tier Risk Policy Threshold Tuner</span>
            </div>
            <button onClick={loadAll} disabled={loadingPolicy} className="btn btn-outline btn-sm">
              <RefreshCw size={12} className={loadingPolicy ? 'spin' : ''} />
              <span>Sync</span>
            </button>
          </div>

          <p className="card-desc" style={{ marginBottom: '1.1rem' }}>
            Tune live operational boundaries separating frictionless auto-approval, Step-Up SMS OTP verification, and automated fraud freeze.
          </p>

          {/* Visual 3-zone bar */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div
              style={{
                height: '16px',
                borderRadius: '8px',
                overflow: 'hidden',
                display: 'flex',
                border: '1px solid var(--border-light)',
              }}
            >
              <div
                style={{ width: `${threshLow * 100}%`, background: 'var(--tier-low)', transition: 'width 0.2s ease' }}
                title={`Low Risk: 0.00 - ${threshLow.toFixed(2)}`}
              />
              <div
                style={{
                  width: `${Math.max(0, (threshHigh - threshLow) * 100)}%`,
                  background: 'var(--tier-med)',
                  transition: 'width 0.2s ease',
                }}
                title={`Medium Risk: ${threshLow.toFixed(2)} - ${threshHigh.toFixed(2)}`}
              />
              <div
                style={{ width: `${Math.max(0, (1 - threshHigh) * 100)}%`, background: 'var(--tier-high)', transition: 'width 0.2s ease' }}
                title={`High Risk: ${threshHigh.toFixed(2)} - 1.00`}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginTop: '0.35rem', color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--tier-low)' }}>LOW (&lt; {threshLow.toFixed(2)})</span>
              <span style={{ color: 'var(--tier-med)' }}>OTP CHALLENGE ({threshLow.toFixed(2)} – {threshHigh.toFixed(2)})</span>
              <span style={{ color: 'var(--tier-high)' }}>BLOCK (&ge; {threshHigh.toFixed(2)})</span>
            </div>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Low / Medium Threshold (OTP Trigger):</span>
              <strong style={{ color: 'var(--tier-med)' }}>{threshLow.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              min="0.15"
              max="0.70"
              step="0.05"
              value={threshLow}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                setThreshLow(Math.min(v, threshHigh - 0.10));
              }}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Medium / High Threshold (Auto-Block):</span>
              <strong style={{ color: 'var(--tier-high)' }}>{threshHigh.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              min="0.45"
              max="0.95"
              step="0.05"
              value={threshHigh}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                setThreshHigh(Math.max(v, threshLow + 0.10));
              }}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.65rem', marginTop: 'auto', paddingTop: '0.5rem' }}>
            <button
              type="button"
              onClick={() => handleApplyThresholds(threshLow, threshHigh)}
              className="btn btn-primary btn-sm"
              style={{ flex: 1 }}
            >
              <CheckCircle2 size={14} />
              <span>Apply Live Thresholds</span>
            </button>
            <button
              type="button"
              onClick={() => handleApplyThresholds(0.45, 0.80)}
              className="btn btn-outline btn-sm"
            >
              Reset (0.45 / 0.80)
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Grid: HMAC Gateway Verifier + Defense-in-Depth Posture */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {/* 3. HMAC-SHA256 Gateway Signature Verifier */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
            <div className="card-title" style={{ margin: 0 }}>
              <Key size={18} color="#a855f7" />
              <span>Gateway HMAC-SHA256 & Anti-Replay Tester</span>
            </div>
            <span className="badge" style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c084fc' }}>Constant-Time</span>
          </div>

          <p className="card-desc" style={{ marginBottom: '0.85rem' }}>
            Generate an <code>X-Signature</code> &amp; <code>X-Timestamp</code> pair for any JSON payload, then edit the payload before verifying to test tamper detection (HTTP 403).
          </p>

          <textarea
            className="form-input"
            rows={5}
            value={hmacPayloadText}
            onChange={(e) => setHmacPayloadText(e.target.value)}
            style={{ fontFamily: 'Consolas, monospace', fontSize: '0.75rem', marginBottom: '0.75rem' }}
          />

          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.85rem' }}>
            <button type="button" onClick={handleSignPayload} disabled={hmacBusy} className="btn btn-outline btn-sm">
              <FileCode size={14} color="#a855f7" />
              <span>1. Sign Payload</span>
            </button>
            <button type="button" onClick={handleVerifyPayload} disabled={hmacBusy || !hmacResult} className="btn btn-primary btn-sm">
              <Send size={14} />
              <span>2. Verify Signature</span>
            </button>
          </div>

          {hmacResult && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                padding: '0.7rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                fontSize: '0.72rem',
                marginBottom: '0.75rem',
                wordBreak: 'break-all',
              }}
            >
              <div><strong>X-Timestamp:</strong> <code>{hmacResult.timestamp}</code></div>
              <div style={{ marginTop: '0.25rem' }}><strong>X-Signature:</strong> <code style={{ color: '#c084fc' }}>{hmacResult.signature}</code></div>
            </div>
          )}

          {verifyResult && (
            <div
              style={{
                padding: '0.7rem',
                borderRadius: '6px',
                fontSize: '0.78rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: verifyResult.ok ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: `1px solid ${verifyResult.ok ? '#10b981' : '#ef4444'}`,
                color: verifyResult.ok ? '#34d399' : '#f87171',
              }}
            >
              {verifyResult.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              <span>{verifyResult.ok ? verifyResult.data?.message : `Tampering Rejected: ${verifyResult.error}`}</span>
            </div>
          )}
        </div>

        {/* 4. Defense-in-Depth Security & Privacy Posture */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
            <div className="card-title" style={{ margin: 0 }}>
              <Lock size={18} color="#10b981" />
              <span>Defense-in-Depth Security Posture</span>
            </div>
            <span className="badge badge-low">Active Hardening</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.78rem' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--accent-cyan)', fontWeight: 700, marginBottom: '0.25rem' }}>
                DPDP Act 2023 Data Privacy
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                {posture?.privacy_compliance?.pii_storage || 'Zero plaintext mobile numbers or banking credentials'} •{' '}
                {posture?.privacy_compliance?.pseudonymization || 'Salted SHA-256 with server key derivation'}
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: '#a855f7', fontWeight: 700, marginBottom: '0.25rem' }}>
                Token Bucket Rate Limiting
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                Rate: <strong>{posture?.rate_limiting?.rate_per_minute ?? 120} req/min</strong> •{' '}
                Burst Capacity: <strong>{posture?.rate_limiting?.burst_capacity ?? 40} tokens</strong> •{' '}
                Status: <strong>{posture?.rate_limiting?.enabled ? 'Enforced' : 'Bypassed'}</strong>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: '#34d399', fontWeight: 700, marginBottom: '0.25rem' }}>
                OWASP HTTP Security Headers
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                X-Frame-Options: <code>{posture?.http_security_headers?.x_frame_options || 'DENY'}</code> •{' '}
                X-Content-Type-Options: <code>{posture?.http_security_headers?.x_content_type_options || 'nosniff'}</code> •{' '}
                CSP: <code>{posture?.http_security_headers?.csp || 'Enforced'}</code>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: '#fbbf24', fontWeight: 700, marginBottom: '0.25rem' }}>
                SQLite WAL &amp; Cryptographic Ledger
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                {posture?.privacy_compliance?.audit_ledger || 'Append-Only Cryptographic Hash Chain'} • Anti-Replay Window:{' '}
                <strong>{posture?.gateway_authentication?.anti_replay_window_seconds ?? 300}s</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
