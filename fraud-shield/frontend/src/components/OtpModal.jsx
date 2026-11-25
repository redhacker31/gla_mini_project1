import React, { useState, useEffect } from 'react';
import {
  X,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  RefreshCw,
  KeyRound,
  Clock,
} from 'lucide-react';
import { verifyOtp, resendOtp, fetchLatestOtp, fetchOtpSession } from '../services/api';

export default function OtpModal({
  sessionId,
  txnId,
  onClose,
  onSuccess,
  onNotify,
}) {
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [resultMessage, setResultMessage] = useState(null);
  const [resultStatus, setResultStatus] = useState(null); // 'APPROVED', 'ATTEMPT_FAILED', 'LOCKED'
  const [timeLeft, setTimeLeft] = useState(180);
  const [sandboxOtp, setSandboxOtp] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadInfo() {
      try {
        const info = await fetchOtpSession(sessionId);
        if (mounted && info) {
          setSessionInfo(info);
          if (info.expires_at) {
            const expMs = new Date(info.expires_at).getTime();
            const nowMs = Date.now();
            const diffSec = Math.max(0, Math.floor((expMs - nowMs) / 1000));
            if (diffSec >= 0 && diffSec <= 180) {
              setTimeLeft(diffSec);
            }
          }
        }
      } catch (err) {
        console.warn('Could not load session details:', err);
      }
      try {
        const latest = await fetchLatestOtp(sessionId);
        if (mounted && latest?.otp) {
          setSandboxOtp(latest.otp);
        }
      } catch {
        // Ignore if sandbox endpoint is disabled in production
      }
    }
    if (sessionId) {
      loadInfo();
    }
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
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

  const handleSandboxAutofill = async () => {
    try {
      const data = await fetchLatestOtp(sessionId);
      if (data && data.otp) {
        setOtpCode(data.otp);
        setSandboxOtp(data.otp);
        onNotify?.(`Sandbox autofilled OTP: ${data.otp}`, 'info');
      }
    } catch (err) {
      onNotify?.(`Could not fetch sandbox OTP: ${err.message}`, 'error');
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!otpCode || otpCode.length !== 6) {
      setResultMessage('Please enter a valid 6-digit numeric OTP.');
      setResultStatus('ATTEMPT_FAILED');
      return;
    }

    setLoading(true);
    setResultMessage(null);

    try {
      const resp = await verifyOtp(sessionId, otpCode);
      if (resp.success && resp.status === 'APPROVED') {
        setResultStatus('APPROVED');
        setResultMessage(resp.message || 'OTP Verified! Micro-transaction promoted to APPROVED.');
        onNotify?.(`Transaction ${txnId?.substring(0, 8)} approved via Step-Up OTP.`, 'success');
        onSuccess?.();
      } else if (resp.status === 'LOCKED' || resp.status === 'REJECTED') {
        setResultStatus('LOCKED');
        setResultMessage(resp.message || 'Maximum 3 attempts exceeded. Transaction REJECTED.');
        onNotify?.('Transaction rejected due to failed OTP verification.', 'error');
        onSuccess?.();
      } else {
        setResultStatus('ATTEMPT_FAILED');
        setResultMessage(resp.message || `Incorrect OTP. ${resp.remaining_attempts} attempt(s) remaining.`);
      }
    } catch (err) {
      setResultStatus('ATTEMPT_FAILED');
      setResultMessage(err.message || 'Verification request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setResultMessage(null);
    try {
      const resp = await resendOtp(sessionId);
      setTimeLeft(180);
      const latest = await fetchLatestOtp(sessionId).catch(() => null);
      if (latest?.otp) setSandboxOtp(latest.otp);
      onNotify?.(resp.message || 'Fresh OTP dispatched via SMS.', 'info');
    } catch (err) {
      onNotify?.(`Resend failed: ${err.message}`, 'error');
    } finally {
      setResending(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="modal-content">
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            <KeyRound size={20} color="#D97706" />
            <h3 style={{ margin: 0, fontSize: '1.08rem', color: 'var(--text-main)', fontWeight: 700 }}>
              Step-Up OTP Authentication Challenge
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
          {/* Challenge Context Info */}
          <div className="sub-panel" style={{ padding: '1rem', marginBottom: '1.1rem', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Transaction ID:</span>
              <code style={{ color: 'var(--text-main)', fontWeight: 600 }}>{txnId}</code>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Session ID:</span>
              <code style={{ color: 'var(--text-dim)' }}>{sessionId?.substring(0, 22)}...</code>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>SMS Dispatch Destination:</span>
              <strong style={{ color: 'var(--text-main)' }}>
                {sessionInfo?.phone_masked || '+91 98*** **321'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>TTL Window:</span>
              <span
                className="mono"
                style={{
                  color: timeLeft < 30 ? 'var(--tier-high)' : 'var(--tier-med)',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                }}
              >
                <Clock size={12} />
                {formatTime(timeLeft)} remaining
              </span>
            </div>
          </div>

          {/* Simulated SMS Gateway Inbox Notification */}
          {sandboxOtp && (
            <div
              style={{
                background: 'var(--accent-coral-tint)',
                border: '1px solid var(--accent-coral-border)',
                borderRadius: '10px',
                padding: '0.8rem 0.95rem',
                marginBottom: '1.1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem',
                fontSize: '0.78rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Smartphone size={17} color="#E85D3F" />
                <div>
                  <div style={{ color: 'var(--accent-coral-hover)', fontWeight: 700 }}>Simulated Telecom SMS Received</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    Your verification OTP is{' '}
                    <strong className="mono" style={{ color: 'var(--text-main)', letterSpacing: '0.1em' }}>
                      {sandboxOtp}
                    </strong>{' '}
                    (valid 3 min).
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOtpCode(sandboxOtp)}
                className="btn btn-primary btn-sm"
                style={{ whiteSpace: 'nowrap' }}
              >
                Use Code
              </button>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleVerify}>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label className="form-label" style={{ margin: 0 }}>
                  Enter 6-Digit OTP Code
                </label>
                <button
                  type="button"
                  onClick={handleSandboxAutofill}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#BE185D',
                    fontSize: '0.73rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  ⚡ Sandbox Quick-Fill OTP
                </button>
              </div>

              <input
                type="text"
                maxLength={6}
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="• • • • • •"
                className="form-input mono"
                disabled={resultStatus === 'APPROVED' || resultStatus === 'LOCKED'}
                style={{
                  fontSize: '1.55rem',
                  letterSpacing: '0.55rem',
                  textAlign: 'center',
                  fontWeight: 800,
                  padding: '0.75rem',
                }}
                autoFocus
              />
            </div>

            {resultMessage && (
              <div
                style={{
                  padding: '0.8rem',
                  borderRadius: '8px',
                  marginBottom: '1rem',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  background:
                    resultStatus === 'APPROVED'
                      ? 'var(--tier-low-bg)'
                      : resultStatus === 'LOCKED'
                      ? 'var(--tier-high-bg)'
                      : 'var(--tier-med-bg)',
                  border: `1px solid ${
                    resultStatus === 'APPROVED'
                      ? 'var(--tier-low-border)'
                      : resultStatus === 'LOCKED'
                      ? 'var(--tier-high-border)'
                      : 'var(--tier-med-border)'
                  }`,
                  color:
                    resultStatus === 'APPROVED'
                      ? 'var(--tier-low)'
                      : resultStatus === 'LOCKED'
                      ? 'var(--tier-high)'
                      : 'var(--tier-med)',
                }}
              >
                {resultStatus === 'APPROVED' && <CheckCircle2 size={16} />}
                {resultStatus === 'ATTEMPT_FAILED' && <AlertTriangle size={16} />}
                {resultStatus === 'LOCKED' && <ShieldAlert size={16} />}
                <span>{resultMessage}</span>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending || resultStatus === 'APPROVED' || resultStatus === 'LOCKED'}
                className="btn btn-outline"
                style={{ flex: 1 }}
              >
                <RefreshCw size={14} className={resending ? 'spin' : ''} />
                <span>Resend OTP</span>
              </button>

              <button
                type="submit"
                disabled={loading || otpCode.length !== 6 || resultStatus === 'APPROVED' || resultStatus === 'LOCKED'}
                className="btn btn-primary"
                style={{ flex: 1.5 }}
              >
                <span>{loading ? 'Verifying...' : 'Verify OTP Code'}</span>
              </button>
            </div>
          </form>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-outline btn-sm">
            Close Dialog
          </button>
        </div>
      </div>
    </div>
  );
}
