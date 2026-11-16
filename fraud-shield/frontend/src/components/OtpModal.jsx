import React, { useState, useEffect } from 'react';
import { 
  X, 
  Smartphone, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  RefreshCw, 
  KeyRound,
  Clock
} from 'lucide-react';
import { verifyOtp, resendOtp, fetchLatestOtp, fetchOtpSession } from '../services/api';

export default function OtpModal({ 
  sessionId, 
  txnId, 
  onClose, 
  onSuccess,
  onNotify 
}) {
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [resultMessage, setResultMessage] = useState(null);
  const [resultStatus, setResultStatus] = useState(null); // 'APPROVED', 'ATTEMPT_FAILED', 'LOCKED'
  const [timeLeft, setTimeLeft] = useState(180);

  // Load session information on mount
  useEffect(() => {
    let mounted = true;
    async function loadInfo() {
      try {
        const info = await fetchOtpSession(sessionId);
        if (mounted && info) {
          setSessionInfo(info);
        }
      } catch (err) {
        console.warn('Could not load session details:', err);
      }
    }
    if (sessionId) {
      loadInfo();
    }
    return () => { mounted = false; };
  }, [sessionId]);

  // TTL Countdown Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Sandbox helper: autofill OTP
  const handleSandboxAutofill = async () => {
    try {
      const data = await fetchLatestOtp(sessionId);
      if (data && data.otp) {
        setOtpCode(data.otp);
        onNotify?.(`Sandbox autofilled OTP: ${data.otp}`, 'info');
      }
    } catch (err) {
      onNotify?.(`Could not fetch sandbox OTP: ${err.message}`, 'error');
    }
  };

  // Submit OTP Verification
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
        onNotify?.(`Transaction rejected due to failed OTP verification.`, 'error');
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

  // Resend OTP
  const handleResend = async () => {
    setResending(true);
    setResultMessage(null);
    try {
      const resp = await resendOtp(sessionId);
      setTimeLeft(180);
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
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <KeyRound size={20} color="#fbbf24" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#fff', fontWeight: 600 }}>
              Step-Up OTP Authentication Challenge
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
          {/* Challenge Context Info */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.7)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            marginBottom: '1.25rem',
            fontSize: '0.8rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Transaction ID:</span>
              <code style={{ color: '#fff' }}>{txnId}</code>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Session ID:</span>
              <code style={{ color: 'var(--text-dim)' }}>{sessionId?.substring(0, 20)}...</code>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>SMS Dispatch Destination:</span>
              <strong style={{ color: '#fff' }}>
                {sessionInfo?.phone_masked || '+91 98*** **321'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>TTL Window:</span>
              <span style={{
                color: timeLeft < 30 ? '#ef4444' : '#fbbf24',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}>
                <Clock size={12} />
                {formatTime(timeLeft)} remaining
              </span>
            </div>
          </div>

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
                    color: 'var(--accent-cyan)',
                    fontSize: '0.725rem',
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
                className="form-input"
                disabled={resultStatus === 'APPROVED' || resultStatus === 'LOCKED'}
                style={{
                  fontSize: '1.5rem',
                  letterSpacing: '0.5rem',
                  textAlign: 'center',
                  fontWeight: 700,
                  fontFamily: 'Consolas, monospace',
                  padding: '0.75rem',
                }}
                autoFocus
              />
            </div>

            {/* Outcome message */}
            {resultMessage && (
              <div style={{
                padding: '0.75rem',
                borderRadius: '6px',
                marginBottom: '1rem',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 
                  resultStatus === 'APPROVED' ? 'rgba(16, 185, 129, 0.15)' :
                  resultStatus === 'LOCKED' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.15)',
                border: `1px solid ${
                  resultStatus === 'APPROVED' ? '#10b981' :
                  resultStatus === 'LOCKED' ? '#ef4444' : '#f59e0b'
                }`,
                color:
                  resultStatus === 'APPROVED' ? '#34d399' :
                  resultStatus === 'LOCKED' ? '#f87171' : '#fbbf24',
              }}>
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
                className="btn btn-warning"
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
