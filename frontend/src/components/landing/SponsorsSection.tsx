import React from 'react';
import { SponsorsData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { motion } from 'framer-motion';

interface SponsorsSectionProps {
  data: SponsorsData;
}

export function SponsorsSection({ data }: SponsorsSectionProps) {
  return (
    <div className="py-16 bg-[var(--surface)] overflow-hidden">
      <Container className="text-center">
        <motion.h3 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-3xl font-bold text-[var(--ink)] mb-12"
        >
          {data.title}
        </motion.h3>
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-70"
        >
          {data.sponsors.map((sponsor, idx) => (
            <div 
              key={idx} 
              className="text-2xl font-bold text-gray-500 flex items-center gap-2 hover:opacity-100 hover:text-[var(--brand)] hover:scale-105 transition-all duration-300 cursor-pointer"
            >
              <span className="w-6 h-6 bg-gray-400 rounded-sm inline-block transition-colors group-hover:bg-[var(--brand)]"></span>
              {sponsor.name}
            </div>
          ))}
        </motion.div>
      </Container>
    </div>
  );
}
