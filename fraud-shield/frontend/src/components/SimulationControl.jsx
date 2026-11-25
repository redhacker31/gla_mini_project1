import React, { useState } from 'react';
import {
  Play,
  Square,
  Zap,
  ShieldAlert,
  Users,
  TrendingUp,
  ShoppingBag,
  Activity,
} from 'lucide-react';
import { startSimulation, stopSimulation, triggerScenario } from '../services/api';

export default function SimulationControl({
  simStatus,
  onRefresh,
  onNotify,
}) {
  const [loadingAction, setLoadingAction] = useState(false);
  const [tpsRate, setTpsRate] = useState(2.0);
  const [fraudRatio, setFraudRatio] = useState(0.15);
  const [lastScenarioResult, setLastScenarioResult] = useState(null);

  const isRunning = simStatus?.running ?? simStatus?.is_running ?? false;
  const currentTps = simStatus?.rate_tps ?? simStatus?.current_tps ?? tpsRate;

  const handleToggleSimulation = async () => {
    setLoadingAction(true);
    try {
      if (isRunning) {
        await stopSimulation();
        onNotify?.('Simulation stream halted.', 'info');
      } else {
        await startSimulation({
          rate_tps: parseFloat(tpsRate),
          fraud_ratio: parseFloat(fraudRatio),
          burst_interval_seconds: 15,
        });
        onNotify?.(`Simulation stream active at ${tpsRate} TPS.`, 'success');
      }
      onRefresh();
    } catch (err) {
      onNotify?.(`Failed to toggle simulation: ${err.message}`, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleTrigger = async (scenarioType, label) => {
    setLoadingAction(true);
    setLastScenarioResult(null);
    try {
      const result = await triggerScenario(scenarioType, 'user_analyst_test', 3);
      const evaluations = result?.results || result?.evaluations || [];
      const count = result?.transactions_generated ?? result?.count ?? evaluations.length;
      setLastScenarioResult({
        type: label,
        count,
        evaluations,
        data: result,
      });
      onNotify?.(`Triggered scenario: ${label}`, 'success');
      onRefresh();
    } catch (err) {
      onNotify?.(`Scenario execution failed: ${err.message}`, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <Activity size={18} color="#E85D3F" />
          <span>Simulation &amp; Adversarial Attack Streaming Center</span>
        </div>

        {/* Live Simulation Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className={`status-badge ${isRunning ? 'status-online' : 'status-checking'}`}>
            <span className="pulse-dot"></span>
            <span>{isRunning ? `Streaming Active (${currentTps} TPS)` : 'Generator Idle'}</span>
          </div>

          <button
            onClick={handleToggleSimulation}
            disabled={loadingAction}
            className={`btn btn-sm ${isRunning ? 'btn-danger' : 'btn-success'}`}
          >
            {isRunning ? (
              <>
                <Square size={13} />
                <span>Stop Stream</span>
              </>
            ) : (
              <>
                <Play size={13} />
                <span>Start Stream</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stream Configuration Bar */}
      <div
        className="sub-panel"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.5rem',
          flexWrap: 'wrap',
          padding: '0.85rem 1rem',
          marginBottom: '1rem',
          fontSize: '0.8rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Throughput Rate:</span>
          <select
            value={tpsRate}
            onChange={(e) => setTpsRate(e.target.value)}
            disabled={isRunning}
            className="form-select"
            style={{ width: 'auto', padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
          >
            <option value="1.0">1.0 TPS (Low Load)</option>
            <option value="2.0">2.0 TPS (Default)</option>
            <option value="5.0">5.0 TPS (Moderate)</option>
            <option value="10.0">10.0 TPS (Stress Load)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Adversarial Attack Ratio:</span>
          <select
            value={fraudRatio}
            onChange={(e) => setFraudRatio(e.target.value)}
            disabled={isRunning}
            className="form-select"
            style={{ width: 'auto', padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
          >
            <option value="0.05">5% Fraud Injections</option>
            <option value="0.15">15% Fraud Injections (Balanced)</option>
            <option value="0.30">30% High Attack Infiltration</option>
          </select>
        </div>

        <div style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
          Session Emitted: <strong style={{ color: 'var(--text-main)' }}>{simStatus?.total_generated ?? 0}</strong> txns
        </div>
      </div>

      {/* On-Demand Scenario Buttons */}
      <div>
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.55rem' }}>
          On-Demand Adversarial Threat Injections &amp; Testing Scenarios
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
          <button
            onClick={() => handleTrigger('ROUTINE', 'Routine Grocery Micro-Payment')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.7rem 0.9rem' }}
          >
            <ShoppingBag size={16} color="#059669" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: 'var(--text-main)', fontSize: '0.82rem', fontWeight: 700 }}>Routine Commerce</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', fontWeight: 500 }}>Benign kirana INR 15-350</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('VELOCITY_BURST', 'Velocity Rapid-Fire Attack')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.7rem 0.9rem' }}
          >
            <Zap size={16} color="#D97706" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: 'var(--text-main)', fontSize: '0.82rem', fontWeight: 700 }}>Velocity Burst</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', fontWeight: 500 }}>Rapid-fire &lt;15s bursts</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('SMURFING', 'Multi-Mule Smurfing Ring')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.7rem 0.9rem' }}
          >
            <Users size={16} color="#E85D3F" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: 'var(--text-main)', fontSize: '0.82rem', fontWeight: 700 }}>Mule Smurfing</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', fontWeight: 500 }}>Structured micro-transfers</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('BLACKLIST_HIT', 'Blacklisted Syndicate Mule Hit')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.7rem 0.9rem' }}
          >
            <ShieldAlert size={16} color="#DC2626" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: 'var(--text-main)', fontSize: '0.82rem', fontWeight: 700 }}>Blacklist Hit</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', fontWeight: 500 }}>Known mule VPA match</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('AMOUNT_SPIKE', 'Amount Spike Anomaly')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.7rem 0.9rem' }}
          >
            <TrendingUp size={16} color="#BE185D" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: 'var(--text-main)', fontSize: '0.82rem', fontWeight: 700 }}>Amount Spike</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', fontWeight: 500 }}>10x baseline deviation</div>
            </div>
          </button>
        </div>
      </div>

      {/* Scenario Execution Result Banner */}
      {lastScenarioResult && (
        <div
          style={{
            marginTop: '1rem',
            padding: '0.95rem 1.1rem',
            background: 'var(--accent-coral-tint)',
            borderRadius: '10px',
            border: '1px solid var(--accent-coral-border)',
            fontSize: '0.8rem',
            animation: 'fadeIn 0.2s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <span style={{ fontWeight: 700, color: 'var(--accent-coral-hover)' }}>
              Execution Summary: {lastScenarioResult.type}
            </span>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
              Evaluated {lastScenarioResult.count ?? lastScenarioResult.data?.count ?? 0} transactions
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {(lastScenarioResult.evaluations || lastScenarioResult.data?.evaluations || []).map((ev, idx) => (
              <div
                key={idx}
                style={{
                  background: '#FFFFFF',
                  padding: '0.45rem 0.7rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                  Txn #{idx + 1}: ₹{typeof ev.amount === 'number' ? ev.amount.toFixed(2) : ev.amount}
                </span>
                <span
                  className={`badge ${
                    ev.risk_tier === 'LOW' ? 'badge-low' : ev.risk_tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                  }`}
                >
                  {ev.risk_tier} (S={(ev.composite_score ?? 0).toFixed(3)})
                </span>
                <span className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{ev.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
