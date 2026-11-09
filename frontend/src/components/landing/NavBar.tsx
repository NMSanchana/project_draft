import React from 'react';
import Link from 'next/link';
import { NavData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { Menu } from 'lucide-react';

interface NavBarProps {
  data: NavData;
}

export function NavBar({ data }: NavBarProps) {
  return (
    <nav className="absolute top-0 w-full z-50 py-6 animate-fade-down">
      <Container className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-3xl font-bold text-[var(--brand)]">{data.logo}</span>
        </div>
        
        <div className="hidden md:flex items-center space-x-8">
          {data.links.map((link, idx) => (
            <a key={idx} href={link.href} className="text-[var(--ink)] font-medium hover:text-[var(--brand)] transition-colors">
              {link.label}
            </a>
          ))}
        </div>
        
        <div className="hidden md:flex items-center space-x-4">
          <Link href="/en/login" className="text-[var(--ink)] font-medium hover:text-[var(--brand)] transition-colors px-4 py-2">
            {data.loginText}
          </Link>
          <Link href="/en/login" className="bg-[var(--brand)] text-white px-6 py-2 rounded-lg font-medium hover:bg-[var(--brand-hover)] transition-colors">
            {data.signUpText}
          </Link>
        </div>
        
        <button className="md:hidden text-[var(--ink)]">
          <Menu size={24} />
        </button>
      </Container>
    </nav>
  );
}
