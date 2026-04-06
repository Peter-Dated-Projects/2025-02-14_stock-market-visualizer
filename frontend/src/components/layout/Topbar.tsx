'use client';

import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

interface TopbarProps {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/portfolio': 'Portfolio',
  '/trades': 'Trade Ledger',
  '/agent-logic': 'Agent Logic',
  '/system-graph': 'System Graph',
};

export default function Topbar({ theme, onToggleTheme }: TopbarProps) {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] || 'SMV';
  const env = process.env.NEXT_PUBLIC_API_URL?.includes('localhost') ? 'staging' : 'production';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="page-title">{title}</span>
      </div>

      <div className="topbar-center">
        <span className={`env-badge ${env}`}>
          {env}
        </span>
      </div>

      <div className="topbar-right">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
