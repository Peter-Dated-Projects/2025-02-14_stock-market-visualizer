'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { formatCurrency } from '@/lib/formatters';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface PerformanceData {
  range: string;
  current_value: number;
  cash_balance: number;
  holdings_value: number;
  data_points: Array<{ timestamp: string | null; value: number }>;
}

const RANGES = ['1D', '1W', '1M', '3M', '6M'] as const;

export default function PerformanceChart() {
  const [range, setRange] = useState<string>('1M');
  const { data, loading } = useApi<PerformanceData>(`/api/portfolio/performance?range=${range}`);

  // Build chart data — add initial balance as start point for context
  const chartData = [
    { name: 'Start', value: 100000 },
    ...(data?.data_points ?? []).map((dp, i) => ({
      name: dp.timestamp ?? `Point ${i}`,
      value: dp.value,
    })),
  ];

  const currentValue = data?.current_value ?? 100000;
  const isPositive = currentValue >= 100000;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Performance</span>
        <div className="pill-group">
          {RANGES.map((r) => (
            <button
              key={r}
              className={`pill-btn ${range === r ? 'active' : ''}`}
              onClick={() => setRange(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div style={{ width: '100%', height: '220px' }}>
        {loading ? (
          <div className="skeleton" style={{ width: '100%', height: '100%' }} />
        ) : chartData.length <= 1 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
              Performance data will populate with trading activity
            </span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="perfGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={isPositive ? 'var(--green)' : 'var(--red)'}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor={isPositive ? 'var(--green)' : 'var(--red)'}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem',
                }}
                formatter={(value: unknown) => [formatCurrency(Number(value)), 'Value']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={isPositive ? 'var(--green)' : 'var(--red)'}
                strokeWidth={2}
                fill="url(#perfGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
