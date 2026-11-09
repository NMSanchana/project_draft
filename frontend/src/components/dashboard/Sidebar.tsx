'use client';

import React from 'react';
import Link from 'next/link';
import { DASHBOARD_NAV_ITEMS } from '@/data/dashboard/dashboard';
import { DashboardTab } from '@/types/dashboard/dashboard';

interface SidebarProps {
  activeTab: DashboardTab;
  setActiveTab: (tab: DashboardTab) => void;
  isDarkMode?: boolean;
}

export function Sidebar({ activeTab, setActiveTab, isDarkMode = false }: SidebarProps) {
  return (
    <aside
      className={`w-full lg:w-60 p-5 flex flex-col justify-between shrink-0 border-r ${
        isDarkMode
          ? 'bg-[#080c14] border-[#151d2c] text-white'
          : 'bg-[#ffffff] border-[#e2e8f0] text-[#0f172a]'
      }`}
    >
      <div className="space-y-6">
        
        {/* BRAND LOGO */}
        <Link href="/en/landing" className="flex items-center px-3 py-1 focus:outline-none">
          <span className="text-2xl font-black tracking-tight">
            Insight<span className="text-[#10b981]">Flow</span>
          </span>
        </Link>

        {/* MAIN NAVIGATION */}
        <div>
          <p className={`text-[11px] font-bold uppercase tracking-wider px-3 mb-2 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Main
          </p>
          <div className="space-y-1.5">
            {DASHBOARD_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.label;
              return (
                <button
                  key={item.label}
                  onClick={() => setActiveTab(item.label)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-bold cursor-pointer focus:outline-none ${
                    isActive
                      ? isDarkMode
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-xs'
                        : 'bg-[#0f172a] text-white shadow-sm'
                      : isDarkMode
                      ? 'text-slate-300 hover:text-white hover:bg-[#151d2c]'
                      : 'text-slate-600 hover:text-[#0f172a] hover:bg-slate-100'
                  }`}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

      </div>
    </aside>
  );
}
