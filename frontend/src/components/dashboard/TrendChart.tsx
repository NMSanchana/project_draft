'use client';

import React, { useState } from 'react';
import { BarChart2, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendBarItem } from '@/lib/analytics';

interface TrendChartProps {
  isDarkMode?: boolean;
  data?: TrendBarItem[];
  summary?: string;
  badge?: string;
  subtext?: string;
}

export function TrendChart({
  isDarkMode = false,
  data = [],
  summary = '$0',
  badge = 'No active stream',
  subtext = 'Total sales recorded',
}: TrendChartProps) {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const hasData = data && data.length > 0;

  return (
    <div className="space-y-4">
      {/* HEADER ROW WITH DYNAMIC TITLE */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className={`text-base font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            Revenue Trends
          </h3>
          <p className={`text-xs font-medium mt-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
            Periodic sales performance and growth trajectory
          </p>
        </div>

        {hasData && (
          <div className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <TrendingUp size={13} />
            <span>Active Stream</span>
          </div>
        )}
      </div>

      {/* CHART CONTENT OR EMPTY STATE */}
      {!hasData ? (
        <div className={`py-12 flex flex-col items-center justify-center text-center border border-dashed rounded-2xl ${
          isDarkMode ? 'border-[#1a2436] bg-[#080c14]' : 'border-slate-200 bg-slate-50'
        }`}>
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-3 ${
            isDarkMode ? 'bg-[#151d2c] text-slate-400' : 'bg-slate-100 text-slate-400'
          }`}>
            <BarChart2 size={24} />
          </div>
          <h4 className={`text-sm font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            No Revenue Records Yet
          </h4>
          <p className={`text-xs max-w-sm mt-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Ingest your sales CSV data to visualize automated periodic revenue trends.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-end">
          {/* LEFT STAT CARD */}
          <div
            className={`md:col-span-4 p-5 rounded-[24px] border flex flex-col justify-between h-[150px] ${
              isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-[#f8fafc] border-slate-200 shadow-xs'
            }`}
          >
            <div>
              <span className={`text-3xl font-extrabold tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                {summary}
              </span>
              <p className={`text-xs font-medium mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>{subtext}</p>
            </div>

            <div className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full w-fit border border-emerald-500/20">
              <span>{badge}</span>
            </div>
          </div>

          {/* RIGHT CAPSULE BAR GRAPH */}
          <div className="md:col-span-8 flex items-end justify-center md:justify-end gap-3 sm:gap-4 px-2 pt-12 h-[150px]">
            {data.map((item) => {
              const isHovered = hoveredItem === item.name;
              const showTooltip = hoveredItem ? isHovered : item.defaultActive;

              return (
                <div
                  key={item.name}
                  onMouseEnter={() => setHoveredItem(item.name)}
                  onMouseLeave={() => setHoveredItem(null)}
                  className="flex flex-col items-center gap-2 h-full justify-end group relative cursor-pointer"
                >
                  {/* TOOLTIP BADGE */}
                  <AnimatePresence>
                    {showTooltip && (
                      <motion.div
                        initial={{ opacity: 0, y: 6, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 6, scale: 0.9 }}
                        transition={{ duration: 0.15 }}
                        className="absolute -top-11 flex flex-col items-center z-30 pointer-events-none"
                      >
                        <div className="bg-[#0f172a] text-white text-[11px] font-bold px-3 py-1 rounded-full shadow-lg whitespace-nowrap border border-slate-700">
                          {item.value}
                        </div>
                        <div className="w-2.5 h-2.5 rounded-full border-2 border-[#0f172a] bg-white -mt-0.5 shadow-sm" />
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* CAPSULE BAR */}
                  <div className="w-8 sm:w-10 flex items-end justify-center h-full">
                    <motion.div
                      initial={{ height: '0%' }}
                      animate={{ height: item.heightPercent }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                      className={`w-full rounded-full transition-all duration-200 group-hover:scale-105 group-hover:brightness-110 shadow-xs ${item.color}`}
                    />
                  </div>

                  {/* CAPSULE LABEL */}
                  <span
                    className={`text-[11px] font-bold ${
                      showTooltip
                        ? isDarkMode
                          ? 'text-white'
                          : 'text-[#0f172a]'
                        : isDarkMode
                        ? 'text-slate-300'
                        : 'text-slate-500'
                    }`}
                  >
                    {item.name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
