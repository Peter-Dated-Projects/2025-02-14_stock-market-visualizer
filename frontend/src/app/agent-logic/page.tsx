'use client';

import { useApi } from '@/hooks/useApi';
import { timeAgo } from '@/lib/formatters';

interface AgentLog {
  id: string;
  workflow: string;
  ticker: string | null;
  industry: string | null;
  input_summary: string | null;
  sentiment_score: number | null;
  action_recommended: string | null;
  confidence: number | null;
  llm_response: Record<string, unknown> | null;
  created_at: string;
}

interface AgentLogsResponse {
  logs: AgentLog[];
  count: number;
}

const WORKFLOW_COLORS: Record<string, string> = {
  intelligence: '#AF52DE',
  ingestion: '#007AFF',
  signal: '#FF9F0A',
  execution: '#34C759',
};

export default function AgentLogicPage() {
  const { data, loading } = useApi<AgentLogsResponse>('/api/agent/logs?limit=50', {
    immediate: true,
    pollInterval: 10000,
  });

  return (
    <div>
      <div className="card" style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="card-header">
          <span className="card-title" style={{ color: 'var(--green)' }}>
            🤖 Agent Console
          </span>
          <div className="pill-group">
            <button className="pill-btn active">All</button>
            <button className="pill-btn">Intel</button>
            <button className="pill-btn">Ingest</button>
            <button className="pill-btn">Signal</button>
            <button className="pill-btn">Exec</button>
          </div>
        </div>

        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.8rem',
          lineHeight: '1.7',
          maxHeight: '70vh',
          overflowY: 'auto',
          padding: '12px',
        }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[...Array(8)].map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '24px', width: `${60 + Math.random() * 40}%` }} />
              ))}
            </div>
          ) : !data?.logs?.length ? (
            <div style={{ padding: '48px', textAlign: 'center', fontFamily: 'var(--font-sans)' }}>
              <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>🤖 Agent idle</p>
              <span className="text-secondary">
                Logs will stream here when workflows execute
              </span>
            </div>
          ) : (
            data.logs.map((log) => (
              <div
                key={log.id}
                style={{
                  padding: '8px 12px',
                  borderLeft: `3px solid ${WORKFLOW_COLORS[log.workflow] || '#666'}`,
                  marginBottom: '4px',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  background: 'rgba(255,255,255,0.02)',
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '4px' }}>
                  <span className="text-secondary">{timeAgo(log.created_at)}</span>
                  <span className="badge" style={{
                    background: `${WORKFLOW_COLORS[log.workflow]}22`,
                    color: WORKFLOW_COLORS[log.workflow],
                  }}>
                    {log.workflow}
                  </span>
                  {log.ticker && <span className="badge blue">{log.ticker}</span>}
                  {log.action_recommended && (
                    <span className={`badge ${log.action_recommended === 'BUY' ? 'green' : log.action_recommended === 'SELL' ? 'red' : 'yellow'}`}>
                      {log.action_recommended}
                    </span>
                  )}
                  {log.confidence !== null && (
                    <span className="text-secondary">{log.confidence}%</span>
                  )}
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>
                  {log.input_summary}
                </div>
                {log.llm_response && typeof log.llm_response === 'object' && 'reasoning' in log.llm_response && (
                  <div style={{ color: 'var(--text-tertiary)', marginTop: '4px', fontSize: '0.75rem' }}>
                    {String(log.llm_response.reasoning).slice(0, 200)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
