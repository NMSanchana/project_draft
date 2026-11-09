import React from 'react';
import { FeaturesData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { motion } from 'framer-motion';

interface FeaturesSectionProps {
  data: FeaturesData;
}

export function FeaturesSection({ data }: FeaturesSectionProps) {
  return (
    <div className="py-24 bg-white relative">
      <Container>
        <div className="flex flex-col lg:flex-row justify-between items-end mb-16 gap-8">
          <h2 className="text-4xl lg:text-5xl font-bold text-[var(--ink)] leading-tight max-w-lg">
            {data.title}
          </h2>
          <div className="max-w-md flex flex-col items-start lg:items-end text-left lg:text-right">
            <p className="text-[var(--ink-light)] mb-6">
              {data.description}
            </p>
            <button className="bg-[var(--brand)] text-white px-8 py-3 rounded-full font-semibold hover:bg-[var(--brand-hover)] transition-colors shadow-lg shadow-[var(--brand)]/30">
              {data.buttonText}
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {data.cards.map((card, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.15, duration: 0.5 }}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl transition-all duration-300 group"
            >
              <div className="h-48 bg-[#f9fbff] flex items-center justify-center p-6">
                {/* Visual Representation based on imageType */}
                {card.imageType === 'collaboration' && (
                   <div className="w-full h-full relative flex flex-col justify-between">
                      <div className="flex gap-2 mb-2">
                        <div className="w-12 h-16 bg-[#54bd95] opacity-80 rounded-sm"></div>
                        <div className="flex-1 space-y-2 pt-2">
                          <div className="h-2 bg-gray-200 rounded w-full"></div>
                          <div className="h-2 bg-gray-200 rounded w-4/5"></div>
                          <div className="h-2 bg-gray-200 rounded w-full"></div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <div className="w-10 h-10 rounded-full bg-[#e3ebfc]"></div>
                        <div className="w-10 h-10 rounded-full bg-[#2a68e8]"></div>
                        <div className="w-10 h-10 rounded-full bg-[#54bd95] flex items-center justify-center text-white text-xs">...</div>
                      </div>
                   </div>
                )}
                {card.imageType === 'cloud' && (
                  <div className="w-full h-full relative flex items-center justify-center">
                    <div className="absolute inset-0 flex items-end justify-center pb-4 opacity-30 gap-2">
                      <div className="w-2 h-8 bg-green-500 rounded-t-full"></div>
                      <div className="w-2 h-12 bg-green-500 rounded-t-full"></div>
                      <div className="w-2 h-6 bg-green-500 rounded-t-full"></div>
                      <div className="w-2 h-10 bg-green-500 rounded-t-full"></div>
                    </div>
                    <div className="bg-[#54bd95] text-white p-4 rounded-xl w-3/4 relative z-10 shadow-lg">
                      <div className="w-6 h-6 bg-yellow-400 rounded mb-4"></div>
                      <div className="font-bold text-lg mb-1">Document File</div>
                      <div className="text-xs opacity-80">100+ Items</div>
                    </div>
                  </div>
                )}
                {card.imageType === 'analytics' && (
                  <div className="w-full h-full relative flex flex-col justify-center items-center">
                    <div className="w-3/4 mb-4 flex justify-between items-end relative">
                      <svg className="w-full h-16 absolute -top-4" viewBox="0 0 100 50">
                        <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#f0f0f0" strokeWidth="8" strokeLinecap="round" />
                        <path d="M 10 50 A 40 40 0 0 1 50 10" fill="none" stroke="#2a68e8" strokeWidth="8" strokeLinecap="round" />
                        <path d="M 50 10 A 40 40 0 0 1 90 50" fill="none" stroke="#fbbf24" strokeWidth="8" strokeLinecap="round" />
                      </svg>
                      <span className="text-xs font-bold text-gray-500 mt-12">60%</span>
                      <span className="text-xs font-bold text-gray-500 mt-12">40%</span>
                    </div>
                    <div className="w-full flex justify-between gap-2">
                      <div className="flex-1 bg-white p-2 rounded shadow-sm border border-gray-100 flex items-center gap-2">
                         <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center">
                           <div className="w-3 h-2 bg-white rounded-sm"></div>
                         </div>
                         <div className="h-1 bg-green-500 w-full rounded-full"></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-8">
                <h3 className="text-2xl font-bold text-[var(--ink)] mb-4">{card.title}</h3>
                <p className="text-[var(--ink-light)]">{card.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </Container>
    </div>
  );
}
