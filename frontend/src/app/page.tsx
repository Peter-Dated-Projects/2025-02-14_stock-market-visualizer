'use client';

import PortfolioHeader from '@/components/dashboard/PortfolioHeader';
import PerformanceChart from '@/components/dashboard/PerformanceChart';
import IndustryRadar from '@/components/dashboard/IndustryRadar';
import StocksOfInterest from '@/components/dashboard/StocksOfInterest';
import ActivePositions from '@/components/dashboard/ActivePositions';
import RecentTrades from '@/components/dashboard/RecentTrades';

export default function DashboardPage() {
  return (
    <div className="dashboard-grid">
      <PortfolioHeader />
      <PerformanceChart />
      <IndustryRadar />
      <StocksOfInterest />
      <ActivePositions />
      <RecentTrades />
    </div>
  );
}
