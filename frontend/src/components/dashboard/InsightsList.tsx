'use client';

import React from 'react';
import { Sparkles, TrendingUp, AlertTriangle, Lightbulb, Info } from 'lucide-react';
import { RuleInsight } from '@/lib/analytics';

interface InsightsListProps {
  insights?: RuleInsight[];
  isDarkMode?: boolean;
}

export function InsightsList({ insights = [], isDarkMode = false }: InsightsListProps) {
  const hasInsights = insights && insights.length > 0;

  const getIconData = (type: string) => {
    switch (type) {
      case 'growth':
        return { Icon: TrendingUp, bg: isDarkMode ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-600' };
      case 'alert':
        return { Icon: AlertTriangle, bg: isDarkMode ? 'bg-rose-500/20 text-rose-400' : 'bg-rose-100 text-rose-600' };
      case 'opportunity':
        return { Icon: Lightbulb, bg: isDarkMode ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-100 text-amber-600' };
      default:
        return { Icon: Info, bg: isDarkMode ? 'bg-indigo-500/20 text-indigo-400' : 'bg-indigo-100 text-indigo-600' };
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
          Rule-Based Strategic Insights
        </h3>
        {hasInsights && (
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
            isDarkMode ? 'bg-[#1a2436] text-slate-300' : 'bg-slate-100 text-slate-600'
          }`}>
            {insights.length} Rules Fired
          </span>
        )}
      </div>

      {!hasInsights ? (
        <div className={`py-8 px-4 text-center rounded-[20px] border border-dashed flex flex-col items-center justify-center ${
          isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
            isDarkMode ? 'bg-[#151d2c] text-slate-400' : 'bg-slate-100 text-slate-400'
          }`}>
            <Sparkles size={18} />
          </div>
          <h4 className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            No Active Insights Generated
          </h4>
          <p className={`text-[11px] max-w-xs mt-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Upload your sales CSV data to trigger automatic evaluation of growth trends, category margins, and customer loyalty rules.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {insights.map((item) => {
            const { Icon, bg } = getIconData(item.type);
            return (
              <div
                key={item.id}
                className={`p-4 rounded-[20px] border space-y-2 group ${
                  isDarkMode
                    ? 'bg-[#080c14] border-[#1a2436] hover:border-slate-600'
                    : 'bg-[#f8fafc] border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-7 h-7 rounded-full ${bg} flex items-center justify-center shrink-0`}>
                      <Icon size={14} />
                    </div>
                    <h4 className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                      {item.title}
                    </h4>
                  </div>
                  <span className={`text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                    isDarkMode ? 'bg-[#1a2436] text-slate-300' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {item.severity}
                  </span>
                </div>

                <p className={`text-xs font-normal leading-relaxed pl-1 ${
                  isDarkMode ? 'text-slate-300' : 'text-slate-600'
                }`}>
                  {item.desc}
                </p>

                {item.recommendation && (
                  <div className={`pl-1 pt-1.5 border-t text-[11px] font-semibold text-[#10b981] ${
                    isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'
                  }`}>
                    <span className={`font-normal ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      Action:
                    </span>{' '}
                    {item.recommendation}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
