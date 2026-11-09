import React from 'react';
import { Metadata } from 'next';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { Dashboard } from '@/components/dashboard/Dashboard';
import { verifyJwt } from '@/lib/auth';

export const metadata: Metadata = {
  title: 'Settings | InsightFlow Platform',
  description: 'Configure business analytics thresholds, UI theme, and account profile.',
};

export default async function SettingsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;

  // Protect route: Redirect to landing page if token is missing or invalid
  if (!token) {
    redirect('/en/landing');
  }

  const { valid } = await verifyJwt(token);
  if (!valid) {
    redirect('/en/landing');
  }

  return <Dashboard initialTab="Settings" />;
}
