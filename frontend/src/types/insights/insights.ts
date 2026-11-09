import { ProcessedAnalytics, RuleInsight } from '@/lib/analytics';

export type InsightCategory = 'all' | 'growth' | 'alert' | 'opportunity' | 'info';

export interface InsightsViewProps {
  analytics: ProcessedAnalytics | null;
  isDarkMode: boolean;
  onNavigateToUpload: () => void;
}
