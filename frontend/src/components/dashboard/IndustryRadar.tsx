'use client';

import { useApi } from '@/hooks/useApi';

interface IndustryData {
  looking_at: Array<{ name: string; sentiment: number }>;
  avoiding: Array<{ name: string; sentiment: number; reason?: string }>;
}

export default function IndustryRadar() {
  const { data, loading } = useApi<IndustryData>('/api/portfolio/industries', { pollInterval: 60000 });

  const SentimentBar = ({ value }: { value: number }) => {
    const width = Math.abs(value) * 100;
    const color = value >= 0 ? 'var(--green)' : 'var(--red)';
    return (
      <div style={{ width: '100%', height: '4px', background: 'var(--bg-secondary)', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${width}%`, height: '100%', background: color, borderRadius: '2px', transition: 'width 500ms ease' }} />
      </div>
    );
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Industry Radar</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Watching */}
        <div>
          <h4 style={{ color: 'var(--green)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            👀 Watching
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {loading ? (
              [...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: '40px' }} />)
            ) : !data?.looking_at?.length ? (
              <span className="text-secondary" style={{ fontSize: '0.8rem' }}>No industries yet</span>
            ) : (
              data.looking_at.map((ind) => (
                <div key={ind.name} style={{ padding: '8px 10px', background: 'var(--green-bg)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>{ind.name}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--green)', fontWeight: 600 }}>
                      {(ind.sentiment * 100).toFixed(0)}%
                    </span>
                  </div>
                  <SentimentBar value={ind.sentiment} />
                </div>
              ))
            )}
          </div>
        </div>
        {/* Avoiding */}
        <div>
          <h4 style={{ color: 'var(--red)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            🚫 Avoiding
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {loading ? (
              [...Array(2)].map((_, i) => <div key={i} className="skeleton" style={{ height: '40px' }} />)
            ) : !data?.avoiding?.length ? (
              <span className="text-secondary" style={{ fontSize: '0.8rem' }}>None flagged</span>
            ) : (
              data.avoiding.map((ind) => (
                <div key={ind.name} style={{ padding: '8px 10px', background: 'var(--red-bg)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>{ind.name}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--red)', fontWeight: 600 }}>
                      {(ind.sentiment * 100).toFixed(0)}%
                    </span>
                  </div>
                  <SentimentBar value={ind.sentiment} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
