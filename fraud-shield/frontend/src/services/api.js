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
export async function fetchTransactions(limit = 50, userId = null, status = null, riskTier = null) {
  try {
    let endpoint = `/transactions?limit=${limit}`;
    if (userId) endpoint += `&user_id=${encodeURIComponent(userId)}`;
    if (status) endpoint += `&status=${encodeURIComponent(status)}`;
    if (riskTier) endpoint += `&risk_tier=${encodeURIComponent(riskTier)}`;
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
 * Submit Fraud Analyst manual review override for a transaction
 */
export async function reviewTransaction(txnId, decision, analystNote = '', blacklistRecipient = false) {
  return await apiRequest(`/transactions/${encodeURIComponent(txnId)}/review`, {
    method: 'POST',
    body: JSON.stringify({
      decision,
      analyst_note: analystNote,
      blacklist_recipient: blacklistRecipient,
    }),
  });
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

/**
 * Run real-time what-if parametric sensitivity simulation
 */
export async function fetchWhatIfAnalysis(params) {
  return await apiRequest('/explainability/what-if', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Fetch full explainability report for a persisted transaction by ID
 */
export async function fetchTransactionExplanation(txnId) {
  return await apiRequest(`/explainability/transaction/${encodeURIComponent(txnId)}`);
}

/**
 * Compute explainability report for an unpersisted transaction payload
 */
export async function explainTransactionPayload(payload) {
  return await apiRequest('/explainability/explain-transaction', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Retrieve latest performance benchmark report
 */
export async function fetchBenchmarkReport() {
  try {
    return await apiRequest('/system/benchmark/latest');
  } catch (err) {
    console.error('Failed to fetch benchmark report:', err);
    return null;
  }
}

/**
 * Trigger live on-demand SLA latency & concurrency benchmark
 */
export async function runBenchmark(iterations = 30, concurrencyLevels = [10, 25]) {
  return await apiRequest('/system/benchmark/run', {
    method: 'POST',
    body: JSON.stringify({
      iterations,
      concurrency_levels: concurrencyLevels,
    }),
  });
}

/**
 * Retrieve active security controls posture
 */
export async function fetchSecurityStatus() {
  return await apiRequest('/system/security/status');
}

/**
 * Retrieve active blacklisted VPAs and live risk thresholds
 */
export async function fetchBlacklistAndPolicy() {
  return await apiRequest('/system/security/blacklist');
}

/**
 * Add a recipient VPA to the live Risk Engine blacklist
 */
export async function addBlacklistVpa(vpa, reason = 'Added via Security Console') {
  return await apiRequest('/system/security/blacklist', {
    method: 'POST',
    body: JSON.stringify({ vpa, reason }),
  });
}

/**
 * Remove a recipient VPA from the live Risk Engine blacklist
 */
export async function removeBlacklistVpa(vpa) {
  return await apiRequest(`/system/security/blacklist/${encodeURIComponent(vpa)}`, {
    method: 'DELETE',
  });
}

/**
 * Tune composite risk tier boundaries
 */
export async function updateRiskThresholds(thresholdLow, thresholdHigh) {
  return await apiRequest('/system/security/thresholds', {
    method: 'PATCH',
    body: JSON.stringify({
      threshold_low: thresholdLow,
      threshold_high: thresholdHigh,
    }),
  });
}

/**
 * Generate HMAC-SHA256 gateway signature for sandbox testing
 */
export async function generateHmacSignature(payload) {
  return await apiRequest('/system/security/generate-signature', {
    method: 'POST',
    body: JSON.stringify({ payload }),
  });
}

/**
 * Verify HMAC-SHA256 gateway signature against backend
 */
export async function verifyHmacSignature(payload, signature, timestamp) {
  return await apiRequest('/system/security/verify-signature', {
    method: 'POST',
    headers: {
      'X-Signature': signature,
      'X-Timestamp': String(timestamp),
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Seed realistic sample micro-transactions for immediate prototype demonstration
 */
export async function seedDemoTraffic() {
  return await apiRequest('/system/security/demo/seed', {
    method: 'POST',
  });
}
