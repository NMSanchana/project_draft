import { ProcessedAnalytics } from '@/lib/analytics';

export type ReportType = 'executive' | 'revenue' | 'activity' | 'custom';
export type ReportFormat = 'csv' | 'json' | 'pdf';

export interface ReportTemplate {
  id: ReportType;
  title: string;
  description: string;
  metrics: string[];
}

export interface ReportsViewProps {
  analytics: ProcessedAnalytics | null;
  isDarkMode: boolean;
  onNavigateToUpload: () => void;
}
