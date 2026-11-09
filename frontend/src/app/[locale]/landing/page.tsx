import React from 'react';
import { Metadata } from 'next';
import LandingClient from '@/components/landing/LandingClient';
import { landingDataEn } from '@/data/landing/en';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { locale } = await params;
  
  return {
    title: locale === 'en' ? 'InsightFlow - Business Insight Platform' : 'InsightFlow',
    description: locale === 'en' ? "Turn business data into actionable growth decisions." : 'InsightFlow',
  };
}

export async function generateStaticParams() {
  return [
    { locale: 'en' },
  ];
}

export default async function LandingPage({ params }: PageProps) {
  const { locale } = await params;
  // Fallback to English data if locale isn't fully supported yet
  const data = locale === 'en' ? landingDataEn : landingDataEn;

  return <LandingClient data={data} locale={locale} />;
}
