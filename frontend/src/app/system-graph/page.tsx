'use client';

import { useApi } from '@/hooks/useApi';

interface WorkflowInfo {
  name: string;
  last_run: string | null;
  next_run: string | null;
  status: string;
  run_count: number;
}

interface ScheduleInfo {
  scheduler_running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run: string | null;
    trigger: string;
  }>;
  market: {
    is_open: boolean;
    is_trading_day: boolean;
    minutes_until_open: number | null;
    minutes_until_close: number | null;
  };
}

interface WorkflowsResponse {
  workflows: WorkflowInfo[];
}

const WORKFLOW_META: Record<string, { icon: string; description: string; schedule: string }> = {
  intelligence: {
    icon: '🧠',
    description: 'Scrapes news, analyzes industry sentiment via LLM',
    schedule: 'Every 60 min',
  },
  ingestion: {
    icon: '📡',
    description: 'Fetches live prices, detects entry/exit crossings',
    schedule: 'Every 5 min (market hours)',
  },
  signal: {
    icon: '📊',
    description: 'Combines price + sentiment for trade signals',
    schedule: 'Every 15 min (market hours)',
  },
  execution: {
    icon: '⚡',
    description: 'Executes trades via paper engine or IBKR',
    schedule: 'Event-driven',
  },
};

const STATUS_COLORS: Record<string, string> = {
  idle: 'var(--text-tertiary)',
  running: 'var(--green)',
  error: 'var(--red)',
};

export default function SystemGraphPage() {
  const { data: workflows } = useApi<WorkflowsResponse>('/api/system/workflows', { pollInterval: 5000 });
  const { data: schedule } = useApi<ScheduleInfo>('/api/system/schedule', { pollInterval: 5000 });

  return (
    <div>
      {/* Market Status */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <span className="card-title">Market Status</span>
          <span className={`badge ${schedule?.market?.is_open ? 'green' : 'red'}`}>
            {schedule?.market?.is_open ? '● OPEN' : '● CLOSED'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '32px', fontSize: '0.85rem' }}>
          <div>
            <span className="text-secondary">Trading Day: </span>
            <span>{schedule?.market?.is_trading_day ? 'Yes' : 'No'}</span>
          </div>
          {schedule?.market?.minutes_until_open !== null && schedule?.market?.minutes_until_open !== undefined && (
            <div>
              <span className="text-secondary">Opens in: </span>
              <span>{Math.floor(schedule.market.minutes_until_open / 60)}h {schedule.market.minutes_until_open % 60}m</span>
            </div>
          )}
          {schedule?.market?.minutes_until_close !== null && schedule?.market?.minutes_until_close !== undefined && (
            <div>
              <span className="text-secondary">Closes in: </span>
              <span>{Math.floor(schedule.market.minutes_until_close / 60)}h {schedule.market.minutes_until_close % 60}m</span>
            </div>
          )}
          <div>
            <span className="text-secondary">Scheduler: </span>
            <span className={schedule?.scheduler_running ? 'text-green' : 'text-red'}>
              {schedule?.scheduler_running ? 'Running' : 'Stopped'}
            </span>
          </div>
        </div>
      </div>

      {/* Workflow Pipeline */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <span className="card-title">Workflow Pipeline</span>
        </div>

        {/* Pipeline visualization */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '24px 0',
          flexWrap: 'wrap',
        }}>
          {['intelligence', 'ingestion', 'signal', 'execution'].map((name, i) => {
            const meta = WORKFLOW_META[name];
            const wf = workflows?.workflows?.find((w) => w.name === name);
            const statusColor = STATUS_COLORS[wf?.status || 'idle'];

            return (
              <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  padding: '16px 20px',
                  background: 'var(--bg-secondary)',
                  border: `2px solid ${statusColor}`,
                  borderRadius: 'var(--radius)',
                  textAlign: 'center',
                  minWidth: '160px',
                  transition: 'all 200ms',
                }}>
                  <div style={{ fontSize: '1.5rem', marginBottom: '4px' }}>{meta.icon}</div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', textTransform: 'capitalize' }}>{name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {meta.schedule}
                  </div>
                  <div style={{
                    marginTop: '8px',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: statusColor,
                    textTransform: 'uppercase',
                  }}>
                    ● {wf?.status || 'idle'}
                  </div>
                  {wf?.run_count ? (
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                      {wf.run_count} runs
                    </div>
                  ) : null}
                </div>
                {i < 3 && (
                  <span style={{ fontSize: '1.2rem', color: 'var(--text-tertiary)' }}>→</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Scheduled Jobs */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Scheduled Jobs</span>
        </div>
        {schedule?.jobs?.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Name</th>
                <th>Next Run</th>
                <th>Trigger</th>
              </tr>
            </thead>
            <tbody>
              {schedule.jobs.map((job) => (
                <tr key={job.id}>
                  <td className="text-mono">{job.id}</td>
                  <td>{job.name}</td>
                  <td className="text-secondary">
                    {job.next_run ? new Date(job.next_run).toLocaleString() : '—'}
                  </td>
                  <td className="text-secondary text-mono" style={{ fontSize: '0.75rem' }}>
                    {job.trigger}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '32px', textAlign: 'center' }}>
            <span className="text-secondary">Scheduler not running — start the backend first</span>
          </div>
        )}
      </div>
    </div>
  );
}
