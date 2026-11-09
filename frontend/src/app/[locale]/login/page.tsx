import React from 'react';
import { Metadata } from 'next';
import { LoginCard } from '@/components/login/LoginCard';

export const metadata: Metadata = {
  title: 'Login & Authentication | InsightFlow Platform',
  description: 'Sign in or create an account for real-time business insights.',
};

export default function LoginPage() {
  return <LoginCard />;
}
