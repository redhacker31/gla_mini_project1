/**
 * Fraud Shield Frontend API Service
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

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
