import React from 'react';
import { TestimonialData, CtaFormData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { motion } from 'framer-motion';

interface TestimonialSectionProps {
  testimonialData: TestimonialData;
  formData: CtaFormData;
}

export function TestimonialSection({ testimonialData, formData }: TestimonialSectionProps) {
  return (
    <div className="py-24 bg-[#161c28] overflow-hidden">
      <Container className="grid lg:grid-cols-2 gap-16 items-center">
        {/* Left Column - Testimonial */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-white leading-tight mb-6">
            {testimonialData.title}
          </h2>
          <p className="text-gray-400 text-lg mb-12 leading-relaxed max-w-md">
            {testimonialData.subtitle}
          </p>
          
          <div className="mb-8">
             <div className="text-[#54bd95] opacity-60 text-6xl font-serif italic mb-4">"</div>
             <p className="text-gray-300 text-lg mb-6 leading-relaxed">
               {testimonialData.quote}
             </p>
             <p className="text-white font-medium">
               {testimonialData.author}
             </p>
          </div>


        </motion.div>

        {/* Right Column - Form */}
        <motion.div 
          initial={{ opacity: 0, x: 40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="bg-[#222938] rounded-3xl p-10 lg:p-12 shadow-2xl flex flex-col items-center max-w-lg mx-auto w-full border border-white/5 hover:border-[#54bd95]/30 transition-all duration-300"
        >
          <div className="w-16 h-16 bg-[#54bd95] rounded-full flex items-center justify-center mb-6 shadow-lg shadow-[#54bd95]/20 animate-pulse-glow">
             <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
               <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
               <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
               <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
             </svg>
          </div>
          <h3 className="text-3xl font-bold text-white mb-8">{formData.title}</h3>
          
          <form className="w-full space-y-6" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-2">
              <label className="text-white font-medium text-sm">{formData.emailLabel}</label>
              <input 
                type="email" 
                placeholder={formData.emailPlaceholder}
                className="w-full bg-white rounded-lg px-4 py-3 outline-none text-black focus:ring-2 focus:ring-[#54bd95] transition-all duration-200"
              />
            </div>
            <div className="space-y-2">
              <label className="text-white font-medium text-sm">{formData.messageLabel}</label>
              <textarea 
                placeholder={formData.messagePlaceholder}
                rows={4}
                className="w-full bg-white rounded-lg px-4 py-3 outline-none text-black resize-none focus:ring-2 focus:ring-[#54bd95] transition-all duration-200"
              ></textarea>
            </div>
            <button className="w-full bg-[#54bd95] text-white py-4 rounded-lg font-bold hover:bg-[#45a07c] transform hover:-translate-y-0.5 transition-all duration-200 shadow-lg shadow-[#54bd95]/20">
              {formData.buttonText}
            </button>
            <div className="text-center">
              <span className="text-gray-400 text-sm hover:text-white cursor-pointer transition-colors">
                {formData.altText}
              </span>
            </div>
          </form>
        </motion.div>
      </Container>
    </div>
  );
}
