import React from 'react';
import { FooterData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface FooterProps {
  data: FooterData;
}

export function Footer({ data }: FooterProps) {
  return (
    <motion.footer 
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="bg-[#161c28] pt-20 pb-8 text-white border-t border-gray-800"
    >
      <Container>
        <div className="grid lg:grid-cols-12 gap-12 mb-16">
          {/* Left Column */}
          <div className="lg:col-span-4">
            <h2 className="text-4xl font-bold text-[#54bd95] mb-6">{data.logo}</h2>
            <p className="text-gray-400 mb-8 max-w-xs">{data.description}</p>
            <div className="relative max-w-sm">
              <input 
                type="email" 
                placeholder={data.emailPlaceholder}
                className="w-full bg-[#222938] rounded-full px-6 py-4 outline-none text-white border border-gray-700 focus:border-[#54bd95] transition-colors"
              />
              <button className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#54bd95] w-10 h-10 rounded-full flex items-center justify-center text-white hover:bg-[#45a07c] hover:scale-105 transition-all duration-200">
                <ArrowRight size={20} />
              </button>
            </div>
          </div>
          
          {/* Right Columns (Links) */}
          <div className="lg:col-span-8 grid grid-cols-2 md:grid-cols-3 gap-8">
            {data.linkGroups.map((group, idx) => (
              <div key={idx}>
                <h4 className="font-semibold text-lg mb-6">{group.title}</h4>
                <ul className="space-y-4">
                  {group.links.map((link, linkIdx) => (
                    <li key={linkIdx}>
                      <a href={link.href} className="text-gray-400 hover:text-[#54bd95] transition-colors duration-200 inline-block transform hover:translate-x-1">
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        
        {/* Bottom Bar */}
        <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-gray-800 text-gray-400 text-sm">
          <p className="mb-4 md:mb-0">{data.copyright}</p>
          <div className="flex gap-6">
            {data.bottomLinks.map((link, idx) => (
              <a key={idx} href={link.href} className="hover:text-[#54bd95] transition-colors">
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </Container>
    </motion.footer>
  );
}
