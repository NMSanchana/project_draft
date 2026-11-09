'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  Database,
  CheckCircle2,
  Filter,
} from 'lucide-react';
import { InsightsViewProps, InsightCategory } from '@/types/insights/insights';
import { INSIGHT_FILTER_TABS } from '@/data/insights/insights';

export function InsightsView({ analytics, isDarkMode, onNavigateToUpload }: InsightsViewProps) {
  const [selectedCategory, setSelectedCategory] = useState<InsightCategory>('all');

  // Derive insights dynamically from ingested analytics
  const allInsights = analytics?.insights || [];

  const filteredInsights = allInsights.filter((item) => {
    if (selectedCategory === 'all') return true;
    return item.type === selectedCategory;
  });

  return (
    <div className="flex-1 flex flex-col justify-between space-y-6 min-h-[720px] h-full">
      <div className="space-y-6">
        {/* HEADER SECTION */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="text-[#10b981]" size={22} />
              <h1 className={`text-2xl lg:text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                Strategic Rule Insights
              </h1>
            </div>
            <p className={`text-xs font-semibold mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
              Automated rule evaluations, margin alerts, and growth opportunities.
            </p>
          </div>

          {analytics && (
            <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <CheckCircle2 size={14} />
              <span>{allInsights.length} Evaluated Rules Active</span>
            </div>
          )}
        </div>

        {/* FILTER TABS */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <div className={`flex items-center gap-1.5 mr-2 text-xs font-bold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            <Filter size={13} />
            <span>Filter:</span>
          </div>
          {INSIGHT_FILTER_TABS.map((tab) => {
            const isActive = selectedCategory === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setSelectedCategory(tab.id)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer focus:outline-none ${
                  isActive
                    ? isDarkMode
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-xs'
                      : 'bg-[#0f172a] text-white shadow-sm'
                    : isDarkMode
                    ? 'bg-[#080c14] text-slate-300 hover:text-white border border-[#1a2436]'
                    : 'bg-white text-slate-600 hover:text-[#0f172a] border border-slate-200 shadow-2xs'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* CONTENT: DYNAMIC INSIGHTS OR FULL-HEIGHT CLEAN EMPTY STATE */}
        {filteredInsights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredInsights.map((insight) => {
              const isAlert = insight.type === 'alert';
              const isOpportunity = insight.type === 'opportunity';
              return (
                <div
                  key={insight.id}
                  className={`p-5 rounded-[24px] border transition-all shadow-sm hover:shadow-md flex flex-col justify-between ${
                    isDarkMode
                      ? 'bg-[#0e1523] border-[#1a2436]'
                      : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                          isAlert
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : isOpportunity
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                        }`}
                      >
                        {insight.type}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-400">
                        Rule ID: {insight.id}
                      </span>
                    </div>

                    <div>
                      <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                        {insight.title}
                      </h3>
                      <p className={`text-xs mt-1 leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                        {insight.desc}
                      </p>
                      {insight.recommendation && (
                        <p className="text-xs font-semibold text-emerald-400 mt-2">
                          Recommendation: {insight.recommendation}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className={`mt-4 pt-3 border-t flex items-center justify-between text-xs font-semibold ${isDarkMode ? 'border-[#1a2436] text-slate-400' : 'border-slate-100 text-slate-500'}`}>
                    <span>Source: {analytics?.fileName || 'Uploaded CSV'}</span>
                    <span className="text-[#10b981] flex items-center gap-1">
                      Verified Metric <ArrowRight size={12} />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* FULL-HEIGHT CLEAN EMPTY STATE */
          <div
            className={`min-h-[480px] p-12 rounded-[24px] border text-center flex flex-col items-center justify-center space-y-4 ${
              isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-xs'
            }`}
          >
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-[#10b981] flex items-center justify-center">
              <Sparkles size={28} />
            </div>
            <div className="max-w-md space-y-1">
              <h3 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                No Rule Insights Available
              </h3>
              <p className={`text-xs ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
                {analytics
                  ? 'No insights match the current filter selection.'
                  : 'Upload a sales CSV dataset on the Dashboard to trigger real-time rule evaluations, margin anomaly checks, and strategic recommendations.'}
              </p>
            </div>
            {!analytics && (
              <button
                onClick={onNavigateToUpload}
                className="mt-2 px-5 py-2.5 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-sm focus:outline-none"
              >
                <Database size={14} />
                <span>Go to Overview & Upload Data</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
