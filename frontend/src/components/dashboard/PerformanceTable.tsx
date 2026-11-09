'use client';

import React from 'react';
import { IngestionActivity } from '@/lib/analytics';
import { Database, FileCheck } from 'lucide-react';

interface PerformanceTableProps {
  activities?: IngestionActivity[];
  isDarkMode?: boolean;
}

export function PerformanceTable({ activities = [], isDarkMode = false }: PerformanceTableProps) {
  const hasData = activities && activities.length > 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className={`text-base font-extrabold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
          Ingestion & Pipeline Telemetry
        </h3>
        {hasData && (
          <span className={`text-xs font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            {activities.length} {activities.length === 1 ? 'dataset log' : 'dataset logs'}
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-medium border-separate border-spacing-y-2">
          <thead>
            <tr className={`font-semibold border-b ${isDarkMode ? 'text-slate-400 border-[#1a2436]' : 'text-slate-500 border-slate-200'}`}>
              <th className="pb-1.5 pl-3">Dataset / Pipeline Task</th>
              <th className="pb-1.5">Processed Time</th>
              <th className="pb-1.5">Validation Accuracy</th>
              <th className="pb-1.5">Execution Duration</th>
              <th className="pb-1.5 pr-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {!hasData ? (
              <tr>
                <td
                  colSpan={5}
                  className={`py-8 text-center rounded-2xl border border-dashed ${
                    isDarkMode ? 'bg-[#080c14] border-[#1a2436] text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}
                >
                  <div className="flex flex-col items-center justify-center gap-1.5">
                    <Database size={20} className={isDarkMode ? 'text-slate-500' : 'text-slate-400'} />
                    <p className={`font-bold text-xs ${isDarkMode ? 'text-slate-200' : 'text-slate-700'}`}>
                      No Data Ingestion Telemetry Recorded
                    </p>
                    <p className={`text-[11px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      Upload sales CSV records to view automated data processing and validation logs.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              activities.map((row) => (
                <tr
                  key={row.id}
                  className={`rounded-2xl border ${
                    isDarkMode
                      ? 'bg-[#080c14] hover:bg-[#121927] border-[#1a2436] text-slate-200'
                      : 'bg-[#f8fafc] hover:bg-slate-100 border-slate-200 text-slate-700'
                  }`}
                >
                  <td className={`py-3 pl-3 font-bold rounded-l-2xl ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    <div className="flex items-center gap-2">
                      <FileCheck size={15} className="text-[#10b981] shrink-0" />
                      <span>{row.task}</span>
                      <span className={`text-[11px] font-normal ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        ({row.fileName})
                      </span>
                    </div>
                  </td>
                  <td className={`py-3 font-medium ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>{row.date}</td>
                  <td className="py-3 font-bold text-emerald-400">{row.accuracy}</td>
                  <td className={`py-3 font-medium ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>{row.duration}</td>
                  <td className="py-3 pr-3 rounded-r-2xl">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full fill-current bg-current" />
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
