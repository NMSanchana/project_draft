import React from 'react';

export type DashboardTab = 'Dashboard' | 'Insights' | 'Reports' | 'Documents' | 'Settings';

export interface NavItem {
  label: DashboardTab;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  href: string;
}

export interface UserProfile {
  id?: string;
  name: string;
  email: string;
  avatar?: string;
}
