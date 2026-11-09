import { InsightCategory } from '@/types/insights/insights';

export const INSIGHT_FILTER_TABS: { id: InsightCategory; label: string }[] = [
  { id: 'all', label: 'All Insights' },
  { id: 'growth', label: 'Growth' },
  { id: 'alert', label: 'Margin & Risk Alerts' },
  { id: 'opportunity', label: 'Opportunities' },
  { id: 'info', label: 'System Telemetry' },
];
