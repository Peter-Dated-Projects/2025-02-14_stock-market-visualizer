'use client';

import { useApi } from '@/hooks/useApi';
import { formatCurrency, formatDateTime } from '@/lib/formatters';

interface Trade {
  id: number;
  ticker: string;
  action: string;
  order_type: string;
  status: string;
  quantity: number;
  exec_price: number | null;
  total_value: number | null;
  paper_flag: boolean;
  confidence: number | null;
  created_at: string;
}

export default function TradesPage() {
  const { data, loading } = useApi<Trade[]>('/api/trades/recent?limit=50');

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Trade Ledger</span>
          <div className="pill-group">
            <button className="pill-btn active">All</button>
            <button className="pill-btn">Buys</button>
            <button className="pill-btn">Sells</button>
          </div>
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton" style={{ height: '44px', width: '100%' }} />
            ))}
          </div>
        ) : !data?.length ? (
          <div style={{ padding: '48px', textAlign: 'center' }}>
            <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>📋 No trades yet</p>
            <span className="text-secondary">
              Trades will appear here as the agent executes them
            </span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Ticker</th>
                <th>Action</th>
                <th>Type</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total</th>
                <th>Status</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {data.map((trade) => (
                <tr key={trade.id}>
                  <td className="text-secondary" style={{ fontSize: '0.8rem' }}>
                    {formatDateTime(trade.created_at)}
                  </td>
                  <td><span className="badge blue">{trade.ticker}</span></td>
                  <td>
                    <span className={`badge ${trade.action === 'BUY' ? 'green' : 'red'}`}>
                      {trade.action}
                    </span>
                  </td>
                  <td className="text-secondary">{trade.order_type}</td>
                  <td>{trade.quantity}</td>
                  <td>{trade.exec_price ? formatCurrency(trade.exec_price) : '—'}</td>
                  <td>{trade.total_value ? formatCurrency(trade.total_value) : '—'}</td>
                  <td>
                    <span className={`badge ${trade.status === 'FILLED' ? 'green' : 'yellow'}`}>
                      {trade.status}
                    </span>
                  </td>
                  <td className="text-secondary">
                    {trade.confidence !== null ? `${trade.confidence}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
