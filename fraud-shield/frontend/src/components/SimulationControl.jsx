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
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { startSimulation, stopSimulation, triggerScenario } from '../services/api';

export default function SimulationControl({ 
  simStatus, 
  onRefresh, 
  onNotify 
}) {
  const [loadingAction, setLoadingAction] = useState(false);
  const [tpsRate, setTpsRate] = useState(2.0);
  const [fraudRatio, setFraudRatio] = useState(0.15);
  const [lastScenarioResult, setLastScenarioResult] = useState(null);

  const isRunning = simStatus?.is_running ?? false;

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
          burst_interval_seconds: 15.0,
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
      setLastScenarioResult({
        type: label,
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
          <Activity size={18} color="var(--accent-cyan)" />
          <span>Simulation & Adversarial Attack Streaming Center</span>
        </div>

        {/* Live Simulation Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className={`status-badge ${isRunning ? 'status-online' : 'status-offline'}`}>
            <span className="pulse-dot"></span>
            <span>{isRunning ? `Streaming Active (${simStatus?.current_tps || tpsRate} TPS)` : 'Generator Idle'}</span>
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
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.5rem',
        flexWrap: 'wrap',
        background: 'rgba(15, 23, 42, 0.5)',
        padding: '0.85rem 1rem',
        borderRadius: '8px',
        marginBottom: '1rem',
        border: '1px solid var(--border-color)',
        fontSize: '0.8rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Throughput Rate:</span>
          <select 
            value={tpsRate} 
            onChange={(e) => setTpsRate(e.target.value)}
            disabled={isRunning}
            className="form-select"
            style={{ width: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          >
            <option value="1.0">1.0 TPS (Low Load)</option>
            <option value="2.0">2.0 TPS (Default)</option>
            <option value="5.0">5.0 TPS (Moderate)</option>
            <option value="10.0">10.0 TPS (Stress Load)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Adversarial Attack Frequency:</span>
          <select 
            value={fraudRatio} 
            onChange={(e) => setFraudRatio(e.target.value)}
            disabled={isRunning}
            className="form-select"
            style={{ width: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          >
            <option value="0.05">5% Fraud Injections</option>
            <option value="0.15">15% Fraud Injections (Balanced)</option>
            <option value="0.30">30% High Attack Infiltration</option>
          </select>
        </div>

        <div style={{ marginLeft: 'auto', color: 'var(--text-dim)', fontSize: '0.75rem' }}>
          Total Emitted: <strong style={{ color: '#fff' }}>{simStatus?.total_generated ?? 0}</strong> txns
        </div>
      </div>

      {/* On-Demand Scenario Buttons */}
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
          On-Demand Adversarial Threat Injections & Testing Scenarios
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
          <button
            onClick={() => handleTrigger('ROUTINE', 'Routine Grocery Micro-Payment')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.65rem 0.85rem' }}
          >
            <ShoppingBag size={15} color="#10b981" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Routine Commerce</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Benign kirana INR 80-250</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('VELOCITY_BURST', 'Velocity Rapid-Fire Attack')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.65rem 0.85rem' }}
          >
            <Zap size={15} color="#f59e0b" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Velocity Burst</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Rapid-fire &lt;15s bursts</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('SMURFING', 'Multi-Mule Smurfing Ring')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.65rem 0.85rem' }}
          >
            <Users size={15} color="#ef4444" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Mule Smurfing</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Structured micro-transfers</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('BLACKLIST_HIT', 'Blacklisted Syndicate Mule Hit')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.65rem 0.85rem' }}
          >
            <ShieldAlert size={15} color="#ef4444" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Blacklist Hit</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Known mule VPA match</div>
            </div>
          </button>

          <button
            onClick={() => handleTrigger('AMOUNT_SPIKE', 'Amount Spike Anomaly')}
            disabled={loadingAction}
            className="btn btn-outline"
            style={{ justifyContent: 'flex-start', padding: '0.65rem 0.85rem' }}
          >
            <TrendingUp size={15} color="#8b5cf6" />
            <div style={{ textAlign: 'left' }}>
              <div style={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Amount Spike</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>10x baseline deviation</div>
            </div>
          </button>
        </div>
      </div>

      {/* Scenario Execution Result Banner */}
      {lastScenarioResult && (
        <div style={{
          marginTop: '1rem',
          padding: '0.85rem 1rem',
          background: 'rgba(30, 41, 59, 0.7)',
          borderRadius: '6px',
          border: '1px solid var(--accent-cyan)',
          fontSize: '0.8rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
              Execution Summary: {lastScenarioResult.type}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>
              Evaluated {lastScenarioResult.data?.count ?? 0} transactions
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {lastScenarioResult.data?.evaluations?.map((ev, idx) => (
              <div 
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.8)',
                  padding: '0.4rem 0.65rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <span>Txn #{idx + 1}: ₹{ev.amount}</span>
                <span className={`badge ${
                  ev.risk_tier === 'LOW' ? 'badge-low' : 
                  ev.risk_tier === 'MEDIUM' ? 'badge-med' : 'badge-high'
                }`}>
                  {ev.risk_tier} (S={ev.composite_score.toFixed(3)})
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{ev.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
