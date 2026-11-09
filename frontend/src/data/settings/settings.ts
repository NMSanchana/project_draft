import { PlatformPreferences, CurrencyCode } from '@/types/settings/settings';

export const CURRENCY_OPTIONS: { code: CurrencyCode; label: string; symbol: string }[] = [
  { code: 'USD', label: 'US Dollar ($)', symbol: '$' },
  { code: 'EUR', label: 'Euro (€)', symbol: '€' },
  { code: 'GBP', label: 'British Pound (£)', symbol: '£' },
  { code: 'INR', label: 'Indian Rupee (₹)', symbol: '₹' },
];

export const DEFAULT_PLATFORM_PREFERENCES: PlatformPreferences = {
  currency: 'USD',
  targetMarginThreshold: 20,
  lowRevenueThreshold: 500,
  emailAlerts: true,
  autoProcessOnUpload: true,
};
