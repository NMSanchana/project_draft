import React from 'react';
import { Metadata } from 'next';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { Dashboard } from '@/components/dashboard/Dashboard';
import { verifyJwt } from '@/lib/auth';

export const metadata: Metadata = {
  title: 'Documents | InsightFlow Platform',
  description: 'Manage ingested CSV spreadsheets, inspect data schemas, and audit column mappings.',
};

export default async function DocumentsPage() {
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

  return <Dashboard initialTab="Documents" />;
}
