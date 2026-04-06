'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency } from '@/lib/formatters';

interface StockOfInterest {
  ticker: string;
  industry: string;
  entry_point: number | null;
  exit_point: number | null;
  confidence: number;
  status: string;
}

export default function StocksOfInterest() {
  const { data, loading } = useApi<StockOfInterest[]>('/api/portfolio/interests', { pollInterval: 30000 });

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Stocks of Interest</span>
        <span className="badge blue">{data?.length ?? 0}</span>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: '48px' }} />)}
        </div>
      ) : !data?.length ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🔭</p>
          <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
            Agent will populate watchlist after its first intelligence run
          </span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {data.map((stock) => (
            <div
              key={stock.ticker}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                transition: 'background 150ms',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="badge blue" style={{ fontWeight: 700 }}>{stock.ticker}</span>
                <span className="text-secondary" style={{ fontSize: '0.8rem' }}>{stock.industry}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.8rem' }}>
                {stock.entry_point && (
                  <span className="text-green">
                    Entry: {formatCurrency(stock.entry_point)}
                  </span>
                )}
                {stock.exit_point && (
                  <span className="text-red">
                    Exit: {formatCurrency(stock.exit_point)}
                  </span>
                )}
                {/* Circular confidence indicator */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: '3px solid',
                  borderColor: stock.confidence >= 70 ? 'var(--green)' : stock.confidence >= 40 ? 'var(--yellow)' : 'var(--text-tertiary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                }}>
                  {stock.confidence}
                </div>
                <span className={`badge ${stock.status === 'ENTERED' ? 'green' : stock.status === 'EXITED' ? 'red' : 'yellow'}`}>
                  {stock.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
