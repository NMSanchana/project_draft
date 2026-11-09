import { LayoutDashboard, Sparkles, FileText, FileCode, Settings } from 'lucide-react';
import { NavItem } from '@/types/dashboard/dashboard';

export const DASHBOARD_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/en/dashboard' },
  { label: 'Insights', icon: Sparkles, href: '/en/dashboard/insights' },
  { label: 'Reports', icon: FileText, href: '/en/dashboard/reports' },
  { label: 'Documents', icon: FileCode, href: '/en/dashboard/documents' },
  { label: 'Settings', icon: Settings, href: '/en/dashboard/settings' },
];
