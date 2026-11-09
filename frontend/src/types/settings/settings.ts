export type CurrencyCode = 'USD' | 'EUR' | 'GBP' | 'INR';

export interface PlatformPreferences {
  currency: CurrencyCode;
  targetMarginThreshold: number;
  lowRevenueThreshold: number;
  emailAlerts: boolean;
  autoProcessOnUpload: boolean;
}

export interface SettingsViewProps {
  user: {
    id?: string;
    name: string;
    email: string;
    avatar?: string;
  };
  onUpdateUser: (updatedUser: { id?: string; name: string; email: string; avatar?: string }) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onResetAnalyticsData?: () => void;
}
