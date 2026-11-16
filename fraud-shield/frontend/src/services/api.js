/**
 * Fraud Shield Frontend API Client Service
 * Connects the React dashboard to the FastAPI backend gateway.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Helper to execute fetch requests with json handling and error propagation
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message = errorBody.detail || errorBody.message || `Request failed with HTTP ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.data = errorBody;
    throw error;
  }

  return await response.json();
}

/**
 * Health check and ML/DB telemetry status
 */
export async function fetchHealthStatus() {
  try {
    let response;
    try {
      response = await fetch(`${API_BASE_URL}/health`);
    } catch {
      // Fallback directly to localhost:8000 if dev proxy is bypassed
      response = await fetch(`http://127.0.0.1:8000/api/v1/health`);
    }

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    return {
      status: 'offline',
      error: err.message,
    };
  }
}

/**
 * Fetch live system telemetry metrics (counts, rates, risk distribution, p95 latency)
 */
export async function fetchDashboardMetrics() {
  try {
    return await apiRequest('/dashboard/metrics');
  } catch (err) {
    console.error('Failed to fetch dashboard metrics:', err);
    return null;
  }
}

/**
 * Real-time transaction risk evaluation
 * Sends payload to POST /api/v1/transactions/evaluate
 */
export async function evaluateTransaction(transactionData) {
  return await apiRequest('/transactions/evaluate', {
    method: 'POST',
    body: JSON.stringify(transactionData),
  });
}

/**
 * Fetch recently evaluated transactions from SQLite persistence
 */
export async function fetchTransactions(limit = 20, userId = null) {
  try {
    let endpoint = `/transactions?limit=${limit}`;
    if (userId) {
      endpoint += `&user_id=${encodeURIComponent(userId)}`;
    }
    return await apiRequest(endpoint);
  } catch (err) {
    console.error('Failed to list transactions:', err);
    return { status: 'error', count: 0, data: [] };
  }
}

/**
 * Fetch single transaction details by transaction ID
 */
export async function fetchTransaction(txnId) {
  return await apiRequest(`/transactions/${encodeURIComponent(txnId)}`);
}

/**
 * Verify cryptographic append-only audit hash chain integrity
 */
export async function verifyAuditLedger() {
  try {
    return await apiRequest('/transactions/audit/verify');
  } catch (err) {
    console.error('Failed to verify audit ledger:', err);
    return {
      status: 'error',
      audit_verification: { valid: false, reason: err.message, records_verified: 0 },
    };
  }
}

/**
 * List audit log records
 */
export async function fetchAuditLogs(limit = 20, entityId = null) {
  try {
    let endpoint = `/transactions/audit/logs?limit=${limit}`;
    if (entityId) {
      endpoint += `&entity_id=${encodeURIComponent(entityId)}`;
    }
    return await apiRequest(endpoint);
  } catch (err) {
    console.error('Failed to list audit logs:', err);
    return { status: 'error', count: 0, data: [] };
  }
}

/**
 * Verify candidate 6-digit OTP
 */
export async function verifyOtp(sessionId, otp) {
  return await apiRequest('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, otp }),
  });
}

/**
 * Resend fresh Step-Up OTP
 */
export async function resendOtp(sessionId) {
  return await apiRequest('/auth/resend-otp', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  });
}

/**
 * Inspect Step-Up OTP Challenge Session State
 */
export async function fetchOtpSession(sessionId) {
  return await apiRequest(`/auth/session/${encodeURIComponent(sessionId)}`);
}

/**
 * Sandbox helper: Retrieve latest dispatched OTP for testing
 */
export async function fetchLatestOtp(sessionId) {
  return await apiRequest(`/auth/latest-otp/${encodeURIComponent(sessionId)}`);
}

/**
 * Query Background Simulation Status
 */
export async function fetchSimulationStatus() {
  try {
    return await apiRequest('/simulation/status');
  } catch (err) {
    console.error('Failed to fetch simulation status:', err);
    return null;
  }
}

/**
 * Start Background Streaming Simulation
 */
export async function startSimulation(config = {}) {
  return await apiRequest('/simulation/start', {
    method: 'POST',
    body: JSON.stringify({
      rate_tps: config.rate_tps || 2.0,
      fraud_ratio: config.fraud_ratio || 0.15,
      burst_interval_seconds: config.burst_interval_seconds || 15.0,
    }),
  });
}

/**
 * Stop Background Streaming Simulation
 */
export async function stopSimulation() {
  return await apiRequest('/simulation/stop', {
    method: 'POST',
  });
}

/**
 * Trigger On-Demand Adversarial or Routine Attack Scenario
 */
export async function triggerScenario(scenario, userId = 'user_sim_test', count = 3) {
  return await apiRequest('/simulation/trigger-scenario', {
    method: 'POST',
    body: JSON.stringify({
      scenario,
      user_id: userId,
      count,
    }),
  });
}
