'use client';

import React from 'react';

interface KPICardsProps {
  revenue?: number;
  orders?: number;
  profitMargin?: number;
  activeUsers?: number;
  accuracy?: number;
  isDarkMode?: boolean;
}

export function KPICards({
  revenue = 0,
  orders = 0,
  profitMargin = 0,
  activeUsers,
  accuracy,
  isDarkMode = false,
}: KPICardsProps) {
  const displayOrders = orders || activeUsers || 0;
  const displayMargin = profitMargin || accuracy || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {/* CARD 1: TOTAL REVENUE */}
      <div
        className={`relative p-5.5 rounded-[26px] flex flex-col justify-between h-[160px] shadow-sm hover:shadow-md transition-shadow group border ${
          isDarkMode
            ? 'bg-[#0e1523] border-[#1a2436]'
            : 'bg-[#fffbeb] border-[#fef3c7]'
        }`}
      >
        <div>
          <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            Total Revenue
          </h3>
          <p className={`text-xs font-medium mt-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
            Aggregated gross sales
          </p>
        </div>
        <div className="flex items-end justify-between">
          <span className={`text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            ${revenue.toLocaleString()}
          </span>
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-base transition-transform group-hover:scale-110 ${
              isDarkMode
                ? 'bg-white/10 text-white border border-white/10 group-hover:bg-[#10b981]'
                : 'bg-[#0f172a] text-white'
            }`}
          >
            ↗
          </div>
        </div>
      </div>

      {/* CARD 2: ORDERS / TRANSACTIONS */}
      <div
        className={`relative p-5.5 rounded-[26px] flex flex-col justify-between h-[160px] shadow-sm hover:shadow-md transition-shadow group border ${
          isDarkMode
            ? 'bg-[#0e1523] border-[#1a2436]'
            : 'bg-[#eff6ff] border-[#dbeafe]'
        }`}
      >
        <div>
          <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            Sales Records
          </h3>
          <p className={`text-xs font-medium mt-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
            Ingested transaction volume
          </p>
        </div>
        <div className="flex items-end justify-between">
          <span className={`text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            {displayOrders.toLocaleString()}
          </span>
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-base transition-transform group-hover:scale-110 ${
              isDarkMode
                ? 'bg-white/10 text-white border border-white/10 group-hover:bg-[#10b981]'
                : 'bg-[#0f172a] text-white'
            }`}
          >
            ↗
          </div>
        </div>
      </div>

      {/* CARD 3: PROFIT MARGIN */}
      <div
        className={`relative p-5.5 rounded-[26px] flex flex-col justify-between h-[160px] shadow-sm hover:shadow-md transition-shadow group border ${
          isDarkMode
            ? 'bg-[#0e1523] border-[#1a2436]'
            : 'bg-[#f0fdf4] border-[#dcfce7]'
        }`}
      >
        <div>
          <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            Profit Margin
          </h3>
          <p className={`text-xs font-medium mt-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
            Deterministic margin ratio
          </p>
        </div>
        <div className="flex items-end justify-between">
          <span className="text-3xl font-black tracking-tight text-emerald-400">
            {typeof displayMargin === 'number' ? displayMargin.toFixed(1) : displayMargin}%
          </span>
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-base transition-transform group-hover:scale-110 ${
              isDarkMode
                ? 'bg-white/10 text-white border border-white/10 group-hover:bg-[#10b981]'
                : 'bg-[#0f172a] text-white'
            }`}
          >
            ↗
          </div>
        </div>
      </div>
    </div>
  );
}
