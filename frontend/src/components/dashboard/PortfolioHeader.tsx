'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency, formatPercent } from '@/lib/formatters';

interface Portfolio {
  cash_balance: number;
  holdings: Array<{ ticker: string; shares: number; avg_cost: number }>;
}

export default function PortfolioHeader() {
  const { data, loading } = useApi<Portfolio>('/api/portfolio', { pollInterval: 30000 });

  const totalHoldings = data?.holdings?.reduce(
    (sum, h) => sum + h.shares * h.avg_cost, 0
  ) ?? 0;
  const totalValue = (data?.cash_balance ?? 100000) + totalHoldings;
  const pnl = totalValue - 100000; // vs initial balance
  const pnlPercent = (pnl / 100000) * 100;

  return (
    <div className="card full-width">
      <div className="card-header">
        <span className="card-title">Portfolio</span>
        <span className="badge blue">
          {data?.holdings?.length ?? 0} positions
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px' }}>
        {loading ? (
          <div className="skeleton" style={{ width: '240px', height: '44px' }} />
        ) : (
          <>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.03em' }}>
              {formatCurrency(totalValue)}
            </h1>
            <span
              className={pnl >= 0 ? 'text-green' : 'text-red'}
              style={{ fontSize: '1.1rem', fontWeight: 600 }}
            >
              {formatCurrency(Math.abs(pnl))} ({formatPercent(pnlPercent)})
            </span>
          </>
        )}
      </div>
      <div style={{ marginTop: '8px', display: 'flex', gap: '24px', fontSize: '0.85rem' }}>
        <span className="text-secondary">
          Cash: <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(data?.cash_balance ?? 100000)}</span>
        </span>
        <span className="text-secondary">
          Holdings: <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(totalHoldings)}</span>
        </span>
        <span className="text-secondary">
          Paper Trading
        </span>
      </div>
    </div>
  );
}
