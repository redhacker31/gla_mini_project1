/**
 * Fraud Shield Frontend API Client Service
 * Connects the React dashboard to the FastAPI backend gateway.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

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
 * Real-time transaction risk evaluation
 * Sends payload to POST /api/v1/transactions/evaluate
 */
export async function evaluateTransaction(transactionData) {
  try {
    const response = await fetch(`${API_BASE_URL}/transactions/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(transactionData),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('Transaction evaluation failed:', err);
    throw err;
  }
}

/**
 * Fetch recently evaluated transactions from SQLite persistence
 */
export async function fetchTransactions(limit = 20, userId = null) {
  try {
    let url = `${API_BASE_URL}/transactions?limit=${limit}`;
    if (userId) {
      url += `&user_id=${encodeURIComponent(userId)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('Failed to list transactions:', err);
    return { status: 'error', count: 0, data: [] };
  }
}

/**
 * Verify cryptographic append-only audit hash chain integrity
 */
export async function verifyAuditLedger() {
  try {
    const response = await fetch(`${API_BASE_URL}/transactions/audit/verify`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('Failed to verify audit ledger:', err);
    return { status: 'error', audit_verification: { valid: false, reason: err.message } };
  }
}
