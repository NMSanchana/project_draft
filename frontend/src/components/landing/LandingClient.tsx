"use client";

import React from 'react';
import { LandingPageData } from '@/types/landing/landing';
import { NavBar } from './NavBar';
import { HeroSection } from './HeroSection';
import { SponsorsSection } from './SponsorsSection';
import { SupportSection } from './SupportSection';
import { FeaturesSection } from './FeaturesSection';
import { TestimonialSection } from './TestimonialSection';
import { Footer } from './Footer';

interface LandingClientProps {
  data: LandingPageData;
  locale: string;
}

export default function LandingClient({ data, locale }: LandingClientProps) {
  return (
    <div className="min-h-screen font-sans bg-white selection:bg-[#54bd95] selection:text-white">
      <NavBar data={data.nav} />
      <HeroSection data={data.hero} locale={locale} />
      <SponsorsSection data={data.sponsors} />
      <SupportSection data={data.support} />
      <FeaturesSection data={data.features} />
      <TestimonialSection testimonialData={data.testimonial} formData={data.ctaForm} />
      <Footer data={data.footer} />
    </div>
  );
}
