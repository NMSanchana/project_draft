'use client';

import React, { useState } from 'react';
import {
  FileText,
  Download,
  Printer,
  FileSpreadsheet,
  CheckCircle2,
  Database,
} from 'lucide-react';
import { ReportsViewProps, ReportType } from '@/types/reports/reports';
import { REPORT_TEMPLATES } from '@/data/reports/reports';

export function ReportsView({ analytics, isDarkMode, onNavigateToUpload }: ReportsViewProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<ReportType>('executive');
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  const activeTemplateObj = REPORT_TEMPLATES.find((t) => t.id === selectedTemplate) || REPORT_TEMPLATES[0];

  // Dynamic report generation and export actions
  const handleExportCsv = () => {
    if (!analytics) return;

    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += `Report,${activeTemplateObj.title}\n`;
    csvContent += `Generated At,${new Date().toISOString()}\n`;
    csvContent += `Source File,${analytics.fileName}\n`;
    csvContent += `Total Revenue,$${analytics.revenue.toFixed(2)}\n`;
    csvContent += `Total Orders,${analytics.orders}\n`;
    csvContent += `Profit Margin,${analytics.profitMargin.toFixed(1)}%\n\n`;

    csvContent += 'Period,Revenue\n';
    analytics.trendData.forEach((row) => {
      csvContent += `${row.name},${row.value}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${selectedTemplate}-report-${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setDownloadSuccess('CSV Report downloaded successfully!');
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  const handleExportJson = () => {
    if (!analytics) return;

    const reportData = {
      template: activeTemplateObj.title,
      generatedAt: new Date().toISOString(),
      source: analytics.fileName,
      metrics: {
        totalRevenue: analytics.revenue,
        totalOrders: analytics.orders,
        profitMargin: analytics.profitMargin,
        trendSummary: analytics.trendSummary,
      },
      periodicTrajectory: analytics.trendData,
      ruleInsights: analytics.insights,
      recentActivities: analytics.activities,
    };

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(reportData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${selectedTemplate}-report-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setDownloadSuccess('JSON Report exported successfully!');
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex-1 flex flex-col justify-between space-y-6 min-h-[720px] h-full">
      <div className="space-y-6">
        {/* HEADER SECTION */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <FileText className="text-[#10b981]" size={22} />
              <h1 className={`text-2xl lg:text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                Reports & Data Exports
              </h1>
            </div>
            <p className={`text-xs font-semibold mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
              Generate and export consolidated executive summaries from ingested records.
            </p>
          </div>

          {downloadSuccess && (
            <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <CheckCircle2 size={14} />
              <span>{downloadSuccess}</span>
            </div>
          )}
        </div>

        {analytics ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* TEMPLATE PICKER (5 COLS) */}
            <div className="lg:col-span-5 space-y-3">
              <p className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                Select Report Template
              </p>
              <div className="space-y-2.5">
                {REPORT_TEMPLATES.map((tmpl) => {
                  const isSelected = selectedTemplate === tmpl.id;
                  return (
                    <button
                      key={tmpl.id}
                      onClick={() => setSelectedTemplate(tmpl.id)}
                      className={`w-full p-4 rounded-[20px] border text-left transition-all cursor-pointer focus:outline-none ${
                        isSelected
                          ? isDarkMode
                            ? 'bg-[#0e1523] border-[#10b981] shadow-md ring-1 ring-[#10b981]/30'
                            : 'bg-white border-[#10b981] shadow-md ring-1 ring-[#10b981]/20'
                          : isDarkMode
                          ? 'bg-[#0e1523]/70 border-[#1a2436] hover:bg-[#0e1523]'
                          : 'bg-white/70 border-slate-200 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <h4 className={`text-sm font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                          {tmpl.title}
                        </h4>
                        {isSelected && <CheckCircle2 size={16} className="text-[#10b981]" />}
                      </div>
                      <p className={`text-xs mt-1 leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                        {tmpl.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {tmpl.metrics.map((m) => (
                          <span
                            key={m}
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${
                              isDarkMode
                                ? 'bg-[#151d2c] text-slate-300 border border-[#222f46]'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* REPORT PREVIEW & EXPORT ACTIONS (7 COLS) */}
            <div
              className={`lg:col-span-7 p-6 rounded-[24px] border space-y-5 ${
                isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-sm'
              }`}
            >
              <div className={`flex items-center justify-between border-b pb-4 ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
                <div>
                  <span className="text-[11px] font-bold text-[#10b981] uppercase tracking-wider">
                    Report Preview
                  </span>
                  <h3 className={`text-lg font-black mt-0.5 ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    {activeTemplateObj.title}
                  </h3>
                </div>
                <span className="text-xs font-semibold text-slate-400">
                  Source: {analytics.fileName}
                </span>
              </div>

              {/* DYNAMIC CALCULATED SUMMARY */}
              <div className="grid grid-cols-3 gap-3">
                <div className={`p-3 rounded-xl border ${isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'}`}>
                  <p className="text-[10px] font-bold uppercase text-slate-400">Total Revenue</p>
                  <p className={`text-base font-black mt-0.5 ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    ${analytics.revenue.toLocaleString()}
                  </p>
                </div>
                <div className={`p-3 rounded-xl border ${isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'}`}>
                  <p className="text-[10px] font-bold uppercase text-slate-400">Record Volume</p>
                  <p className={`text-base font-black mt-0.5 ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    {analytics.orders}
                  </p>
                </div>
                <div className={`p-3 rounded-xl border ${isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'}`}>
                  <p className="text-[10px] font-bold uppercase text-slate-400">Profit Margin</p>
                  <p className="text-base font-black text-emerald-400 mt-0.5">
                    {analytics.profitMargin.toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* PERIODIC TRAJECTORY PREVIEW */}
              <div className="space-y-2">
                <p className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Trajectory Data Points ({analytics.trendData.length} Periods)
                </p>
                <div className={`p-3 rounded-xl border space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar ${
                  isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'
                }`}>
                  {analytics.trendData.map((t, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs font-medium">
                      <span className={`${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>{t.name}</span>
                      <span className={`font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                        {t.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* EXPORT BUTTONS */}
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleExportCsv}
                  className="px-4 py-2.5 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-sm focus:outline-none"
                >
                  <FileSpreadsheet size={14} />
                  <span>Download CSV</span>
                </button>

                <button
                  onClick={handleExportJson}
                  className={`px-4 py-2.5 rounded-xl border text-xs font-bold transition-all flex items-center gap-2 cursor-pointer focus:outline-none ${
                    isDarkMode
                      ? 'border-[#1a2436] bg-[#080c14] hover:bg-[#151d2c] text-white'
                      : 'border-slate-200 hover:bg-slate-50 text-[#0f172a]'
                  }`}
                >
                  <Download size={14} />
                  <span>Export JSON</span>
                </button>

                <button
                  onClick={handlePrint}
                  className={`px-4 py-2.5 rounded-xl border text-xs font-bold transition-all flex items-center gap-2 cursor-pointer focus:outline-none ${
                    isDarkMode
                      ? 'border-[#1a2436] bg-[#080c14] hover:bg-[#151d2c] text-slate-300'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <Printer size={14} />
                  <span>Print Report</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* FULL-HEIGHT CLEAN EMPTY STATE */
          <div
            className={`min-h-[480px] p-12 rounded-[24px] border text-center flex flex-col items-center justify-center space-y-4 ${
              isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-xs'
            }`}
          >
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-[#10b981] flex items-center justify-center">
              <FileText size={28} />
            </div>
            <div className="max-w-md space-y-1">
              <h3 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                No Data Ingested For Reports
              </h3>
              <p className={`text-xs ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
                Upload your business sales CSV file on the Dashboard to generate executive summaries, revenue reports, and downloadable audit logs.
              </p>
            </div>
            <button
              onClick={onNavigateToUpload}
              className="mt-2 px-5 py-2.5 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-sm focus:outline-none"
            >
              <Database size={14} />
              <span>Go to Overview & Upload Data</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
