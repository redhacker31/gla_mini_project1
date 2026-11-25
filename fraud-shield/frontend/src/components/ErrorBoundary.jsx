import React from 'react';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#FAF8F5',
            color: '#1E1916',
            padding: '2rem',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <div
            style={{
              maxWidth: '520px',
              width: '100%',
              background: '#FFFFFF',
              border: '1px solid #FECACA',
              borderRadius: '14px',
              padding: '2rem',
              textAlign: 'center',
              boxShadow: '0 20px 40px rgba(44, 34, 24, 0.12)',
            }}
          >
            <ShieldAlert size={48} color="#DC2626" style={{ margin: '0 auto 1rem' }} />
            <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem', color: '#1E1916' }}>
              Dashboard UI Encountered an Error
            </h2>
            <p style={{ color: '#5C5248', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
              The application recovered from an unexpected rendering exception. Reload the dashboard to restore active telemetry.
            </p>
            {this.state.error?.message && (
              <pre
                style={{
                  background: '#FEF2F2',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  color: '#DC2626',
                  fontSize: '0.75rem',
                  textAlign: 'left',
                  overflowX: 'auto',
                  marginBottom: '1.5rem',
                  border: '1px solid #FECACA',
                }}
              >
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="btn btn-primary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.65rem 1.35rem',
                background: '#E85D3F',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              <RefreshCw size={15} />
              <span>Reload Dashboard</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
