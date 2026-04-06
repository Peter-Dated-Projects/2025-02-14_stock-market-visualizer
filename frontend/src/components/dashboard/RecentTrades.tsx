'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency, timeAgo } from '@/lib/formatters';

interface Trade {
  id: number;
  ticker: string;
  action: string;
  quantity: number;
  exec_price: number | null;
  total_value: number | null;
  paper_flag: boolean;
  created_at: string;
}

export default function RecentTrades() {
  const { data, loading } = useApi<Trade[]>('/api/trades/recent?limit=10', { pollInterval: 15000 });

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Recent Trades</span>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: '44px' }} />)}
        </div>
      ) : !data?.length ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🔄</p>
          <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
            No trades executed yet
          </span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {data.map((trade) => (
            <div
              key={trade.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-secondary)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className={`badge ${trade.action === 'BUY' ? 'green' : 'red'}`}>
                  {trade.action}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{trade.ticker}</span>
                <span className="text-secondary" style={{ fontSize: '0.8rem' }}>
                  ×{trade.quantity}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                  {trade.exec_price ? formatCurrency(trade.exec_price) : '—'}
                </span>
                <span className="text-secondary" style={{ fontSize: '0.75rem' }}>
                  {timeAgo(trade.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
