import { ReportTemplate } from '@/types/reports/reports';

export const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: 'executive',
    title: 'Executive Performance Summary',
    description: 'Consolidated overview of gross revenue, total transaction volume, and overall profit margin ratio.',
    metrics: ['Total Revenue', 'Transaction Count', 'Profit Margin %', 'Rule Insights Count'],
  },
  {
    id: 'revenue',
    title: 'Revenue Trajectory & Trend Report',
    description: 'Detailed periodic sales performance, month-over-month trajectory, and revenue distribution.',
    metrics: ['Periodic Revenue', 'Growth Percentile', 'Peak Sales Period', 'Average Order Value'],
  },
  {
    id: 'activity',
    title: 'Data Ingestion & Operational Audit',
    description: 'Telemetry log of all processed transaction batches, validation statuses, and error audits.',
    metrics: ['Ingestion Timestamps', 'Batch Sizes', 'Processed Rows', 'System Verification Status'],
  },
];
