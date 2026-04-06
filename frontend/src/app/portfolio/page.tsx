'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency, formatPercent } from '@/lib/formatters';

interface Portfolio {
  cash_balance: number;
  holdings: Array<{ ticker: string; shares: number; avg_cost: number }>;
  looking_at_industries: Array<{ name: string; sentiment: number }>;
  avoiding_industries: Array<{ name: string; sentiment: number; reason?: string }>;
}

export default function PortfolioPage() {
  const { data, loading } = useApi<Portfolio>('/api/portfolio');

  return (
    <div>
      <div className="dashboard-grid">
        {/* Cash Balance */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Cash Balance</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 700 }}>
            {loading ? (
              <div className="skeleton" style={{ width: '180px', height: '36px' }} />
            ) : (
              formatCurrency(data?.cash_balance ?? 100000)
            )}
          </h2>
        </div>

        {/* Total Value */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Total Portfolio Value</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 700 }}>
            {loading ? (
              <div className="skeleton" style={{ width: '180px', height: '36px' }} />
            ) : (
              formatCurrency(
                (data?.cash_balance ?? 0) +
                (data?.holdings ?? []).reduce((sum, h) => sum + h.shares * h.avg_cost, 0)
              )
            )}
          </h2>
        </div>

        {/* Holdings Table */}
        <div className="card full-width">
          <div className="card-header">
            <span className="card-title">Holdings</span>
          </div>
          {!data?.holdings?.length ? (
            <div style={{ padding: '32px', textAlign: 'center' }}>
              <span className="text-secondary">No positions yet</span>
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
                {data.holdings.map((h) => (
                  <tr key={h.ticker}>
                    <td><span className="badge blue">{h.ticker}</span></td>
                    <td>{h.shares}</td>
                    <td>{formatCurrency(h.avg_cost)}</td>
                    <td>{formatCurrency(h.shares * h.avg_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
