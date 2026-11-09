/**
 * Core Data Models & Contracts for InsightFlow Platform
 * Used by Frontend & AI / Backend Services
 */

export interface SalesRecord {
  date: string;
  product: string;
  category: string;
  region: string;
  revenue: number;
  cost: number;
  profit: number;
  quantity: number;
  customer: string;
}

export interface TrendBarItem {
  name: string;
  heightPercent: string;
  value: string;
  numericValue: number;
  color: string;
  defaultActive?: boolean;
}

export interface IngestionActivity {
  id: string;
  task: string;
  fileName: string;
  date: string;
  accuracy: string;
  duration: string;
  status: 'Completed' | 'Ready' | 'Processing';
  recordsCount: number;
}

export interface RuleInsight {
  id: string | number;
  title: string;
  desc: string;
  type: 'growth' | 'alert' | 'opportunity' | 'info';
  severity: 'High' | 'Medium' | 'Low' | 'Info';
  recommendation: string;
}

export interface ProcessedAnalytics {
  fileName: string;
  recordsCount: number;
  revenue: number;
  totalCost: number;
  totalProfit: number;
  profitMargin: number;
  orders: number;
  uniqueCustomers: number;
  trendData: TrendBarItem[];
  trendSummary: string;
  trendBadge: string;
  insights: RuleInsight[];
  activities: IngestionActivity[];
  // --- optional fields added by the AI service (additive; existing fields unchanged) ---
  datasetId?: string;
  status?: 'enriching' | 'ready' | 'failed';
  stage?: string;
  quality?: Record<string, unknown>;
  kpis?: Record<string, unknown>;
  ml?: Record<string, unknown>;
}

const STORAGE_KEY = 'insightflow_analytics_cache';

export function getStoredAnalytics(): ProcessedAnalytics | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveStoredAnalytics(data: ProcessedAnalytics): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

export function clearStoredAnalytics(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
