'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency } from '@/lib/formatters';

interface Portfolio {
  holdings: Array<{ ticker: string; shares: number; avg_cost: number }>;
}

export default function ActivePositions() {
  const { data, loading } = useApi<Portfolio>('/api/portfolio', { pollInterval: 30000 });

  const holdings = data?.holdings ?? [];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Active Positions</span>
        <span className="badge blue">{holdings.length}</span>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: '44px' }} />)}
        </div>
      ) : !holdings.length ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{ fontSize: '1.5rem', marginBottom: '8px' }}>📈</p>
          <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
            No positions yet — trades will appear here
          </span>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Shares</th>
              <th>Avg Cost</th>
              <th>Total Value</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.ticker}>
                <td><span className="badge blue">{h.ticker}</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{h.shares}</td>
                <td>{formatCurrency(h.avg_cost)}</td>
                <td style={{ fontWeight: 600 }}>{formatCurrency(h.shares * h.avg_cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
