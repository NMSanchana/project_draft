import React from 'react';
import { SupportData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { Activity, PieChart, Command, Star } from 'lucide-react';
import { motion } from 'framer-motion';

interface SupportSectionProps {
  data: SupportData;
}

const iconMap: Record<string, React.ReactNode> = {
  'activity': <Activity size={24} />,
  'pie-chart': <PieChart size={24} />,
  'command': <Command size={24} />
};

export function SupportSection({ data }: SupportSectionProps) {
  return (
    <div className="py-20 bg-[#fbfbfb]">
      <Container className="grid lg:grid-cols-2 gap-16 items-center">
        {/* Left column */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[var(--ink)] leading-tight mb-6">
            {data.title}
          </h2>
          <p className="text-[var(--ink-light)] text-lg mb-12 leading-relaxed">
            {data.description}
          </p>
          <div className="flex gap-12 flex-wrap">
            {data.stats?.map((stat, idx) => (
              <div key={idx} className="transform hover:scale-105 transition-transform duration-300">
                <p className="text-3xl font-extrabold text-[var(--brand)] mb-1">
                  {stat.value}
                </p>
                <p className="font-bold text-[var(--ink)] text-base">
                  {stat.label}
                </p>
                <p className="text-[var(--ink-light)] text-xs font-medium">
                  {stat.sublabel}
                </p>
              </div>
            ))}
            {data.ratings?.map((rating, idx) => (
              <div key={idx} className="transform hover:scale-105 transition-transform duration-300">
                <div className="flex text-yellow-400 mb-2">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={20} fill={i < Math.floor(rating.score) ? "currentColor" : "transparent"} className={i >= Math.floor(rating.score) ? "text-gray-300" : ""} />
                  ))}
                </div>
                <p className="font-bold text-[var(--ink)] mb-1">
                  {rating.score} / {rating.maxScore} rating
                </p>
                <p className="text-[var(--ink-light)] font-bold text-sm">
                  {rating.company}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Right column */}
        <div className="space-y-8">
          {data.features.map((feature, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.5 }}
              className="flex gap-6 items-start"
            >
              <div className="w-14 h-14 rounded-xl bg-white shadow-md flex items-center justify-center text-[var(--brand)] shrink-0">
                {iconMap[feature.iconName]}
              </div>
              <div>
                <h3 className="text-2xl font-bold text-[var(--ink)] mb-2">{feature.title}</h3>
                <p className="text-[var(--ink-light)] leading-relaxed">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </Container>
    </div>
  );
}
