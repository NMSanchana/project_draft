'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Database,
} from 'lucide-react';
import { Sidebar } from './Sidebar';
import { HeaderBar } from './HeaderBar';
import { KPICards } from './KPICards';
import { TrendChart } from './TrendChart';
import { InsightsList } from './InsightsList';
import { PerformanceTable } from './PerformanceTable';
import { ProfileModal } from './ProfileModal';
import { InsightsView } from '@/components/insights/InsightsView';
import { ReportsView } from '@/components/reports/ReportsView';
import { DocumentsView } from '@/components/documents/DocumentsView';
import { SettingsView } from '@/components/settings/SettingsView';
import { ChatWidget } from '@/components/chat/ChatWidget';
import { DashboardTab } from '@/types/dashboard/dashboard';
import { getCookieToken, decodeJwt, clearAuthCookieAndStorage } from '@/lib/auth';
import {
  ProcessedAnalytics,
  getStoredAnalytics,
  saveStoredAnalytics,
  clearStoredAnalytics,
} from '@/lib/analytics';
import { analyzeDataset, pollDataset, deleteDataset, sendChat, AiServiceError } from '@/lib/aiClient';

interface DashboardProps {
  initialTab?: DashboardTab;
}

export function Dashboard({ initialTab = 'Dashboard' }: DashboardProps) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollAbortRef = useRef<AbortController | null>(null);
  const conversationIdRef = useRef<string | undefined>(undefined);

  // Dynamic logged-in user state (no hardcoded credentials)
  const [user, setUser] = useState<{ id?: string; name: string; email: string; avatar?: string }>({
    id: '',
    name: '',
    email: '',
    avatar: '',
  });

  const [activeTab, setActiveTab] = useState<DashboardTab>(initialTab);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Synchronize dark theme class with html tag and local storage for instant sync without lag
  useEffect(() => {
    const saved = localStorage.getItem('theme');
    if (saved) {
      const isDark = saved === 'dark';
      setIsDarkMode(isDark);
      document.documentElement.classList.toggle('dark', isDark);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const handleToggleTheme = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle('dark', next);
      localStorage.setItem('theme', next ? 'dark' : 'light');
      return next;
    });
  };

  // Analytics dataset state (populated by backend / AI developer pipeline)
  const [analytics, setAnalytics] = useState<ProcessedAnalytics | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Sync tab if initialTab prop changes
  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // Synchronize browser URL bar and back/forward navigation without page refresh
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path.includes('/insights')) setActiveTab('Insights');
      else if (path.includes('/reports')) setActiveTab('Reports');
      else if (path.includes('/documents')) setActiveTab('Documents');
      else if (path.includes('/settings')) setActiveTab('Settings');
      else setActiveTab('Dashboard');
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleTabChange = (tab: DashboardTab) => {
    setActiveTab(tab);
    const routeMap: Record<DashboardTab, string> = {
      Dashboard: '/en/dashboard',
      Insights: '/en/dashboard/insights',
      Reports: '/en/dashboard/reports',
      Documents: '/en/dashboard/documents',
      Settings: '/en/dashboard/settings',
    };
    const targetRoute = routeMap[tab];
    if (targetRoute && typeof window !== 'undefined' && window.location.pathname !== targetRoute) {
      window.history.pushState(null, '', targetRoute);
    }
  };

  useEffect(() => {
    // 1. Verify Authentication Token
    const token = getCookieToken() || localStorage.getItem('token');
    if (!token) {
      router.replace('/en/landing');
      return;
    }

    Promise.resolve(decodeJwt(token)).then(({ valid, payload }) => {
      if (!valid) {
        clearAuthCookieAndStorage();
        router.replace('/en/landing');
        return;
      }

      // If user profile not yet in localStorage, populate from validated JWT payload
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        try {
          const parsed = JSON.parse(storedUser);
          setUser({
            id: parsed.id || payload?.id || '',
            name: parsed.name || payload?.name || '',
            email: parsed.email || payload?.email || '',
            avatar: parsed.avatar || '',
          });
        } catch {
          // fallback
        }
      } else if (payload) {
        setUser({
          id: payload.id || '',
          name: payload.name || '',
          email: payload.email || '',
          avatar: '',
        });
      }
    });

    // 2. Load stored dataset if previously set by backend/AI services
    const stored = getStoredAnalytics();
    if (stored) {
      setAnalytics(stored);
    }
  }, [router]);

  // Stop any background polling when the dashboard unmounts
  useEffect(() => () => pollAbortRef.current?.abort(), []);

  // Poll the AI service until background enrichment (forecast, ML, LLM insights) is ready
  const watchEnrichment = (datasetId: string) => {
    pollAbortRef.current?.abort();
    const controller = new AbortController();
    pollAbortRef.current = controller;
    pollDataset(
      datasetId,
      (data) => {
        setAnalytics(data);
        saveStoredAnalytics(data);
      },
      { signal: controller.signal },
    )
      .then((final) => {
        if (controller.signal.aborted) return;
        if (final?.status === 'failed') {
          setUploadFeedback({ type: 'error', message: 'AI enrichment failed. Core metrics are still available.' });
        } else if (final?.status === 'ready') {
          setUploadFeedback({ type: 'success', message: 'AI analysis complete: insights, forecast and ML results are ready.' });
        }
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setUploadFeedback({
          type: 'error',
          message: err instanceof AiServiceError ? err.message : 'Lost connection to the AI service.',
        });
      });
  };

  // Resume polling if the page was refreshed while a dataset was still enriching
  useEffect(() => {
    const stored = getStoredAnalytics();
    if (stored?.datasetId && stored.status === 'enriching') watchEnrichment(stored.datasetId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle CSV file selection: upload to the AI service, then poll for the enriched result
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setUploadFeedback({ type: 'error', message: 'Only .csv files are supported.' });
      return;
    }

    setIsProcessing(true);
    setUploadFeedback(null);

    pollAbortRef.current?.abort();
    conversationIdRef.current = undefined;

    void (async () => {
      try {
        const result = await analyzeDataset(file);
        setAnalytics(result);
        saveStoredAnalytics(result);
        setUploadFeedback({
          type: 'success',
          message: `File "${file.name}" ingested. Enriching insights in the background...`,
        });
        if (result.datasetId && result.status === 'enriching') watchEnrichment(result.datasetId);
      } catch (err) {
        setUploadFeedback({
          type: 'error',
          message: err instanceof AiServiceError ? err.message : 'Upload failed. Please try again.',
        });
      } finally {
        setIsProcessing(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    })();
  };

  // Clear / Reset dataset to clean zero state
  const handleResetData = () => {
    pollAbortRef.current?.abort();
    const datasetId = analytics?.datasetId;
    clearStoredAnalytics();
    setAnalytics(null);
    setUploadFeedback(null);
    conversationIdRef.current = undefined;
    // Best-effort server cleanup (the UI is already cleared locally)
    if (datasetId) deleteDataset(datasetId).catch(() => undefined);
  };

  // Chat: route the message to the AI service for the active dataset
  const handleSendChat = async (message: string): Promise<string> => {
    const datasetId = analytics?.datasetId;
    if (!datasetId) return 'Upload a CSV first so I have data to analyse.';
    try {
      const reply = await sendChat(datasetId, message, conversationIdRef.current);
      conversationIdRef.current = reply.conversationId || conversationIdRef.current;
      return reply.answer;
    } catch (err) {
      return err instanceof AiServiceError ? err.message : 'Unable to reach the AI analytics service. Please try again.';
    }
  };

  const handleUpdateUser = (updatedUser: { id?: string; name: string; email: string; avatar?: string }) => {
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  };

  return (
    <div
      className={`min-h-screen p-3 md:p-6 font-sans ${
        isDarkMode ? 'bg-[#030712] text-white' : 'bg-[#f1f3f7] text-[#0f172a]'
      }`}
    >
      <div
        className={`w-full max-w-[1600px] mx-auto rounded-[32px] border shadow-2xl flex flex-col lg:flex-row overflow-hidden min-h-[calc(100vh-48px)] ${
          isDarkMode ? 'bg-[#080c14] border-[#151d2c]' : 'bg-[#ffffff] border-slate-200'
        }`}
      >
        {/* LEFT SIDEBAR NAVIGATION */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={handleTabChange}
          isDarkMode={isDarkMode}
        />

        {/* MAIN DASHBOARD CONTENT AREA */}
        <div
          className={`flex-1 flex flex-col p-5 lg:p-7 space-y-6 overflow-y-auto ${
            isDarkMode ? 'bg-[#080c14]' : 'bg-[#f8fafc]'
          }`}
        >
          {/* HEADER BAR: PROMINENT SIGN OUT & PROFESSIONAL AVATAR */}
          <HeaderBar
            user={user}
            onOpenProfile={() => setIsProfileOpen(true)}
            isDarkMode={isDarkMode}
            onToggleDarkMode={handleToggleTheme}
          />

          {/* VIEW SWITCHER BASED ON activeTab */}
          {activeTab === 'Dashboard' && (
            /* 2-COLUMN GRID FIT (8 COLS LEFT, 4 COLS RIGHT) */
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              
              {/* LEFT 8 COLUMNS: GREETING, KPI CARDS, TREND CHART, & PERFORMANCE TABLE */}
              <div className="xl:col-span-8 space-y-5">
                
                {/* DYNAMIC GREETING BASED ON ACTUAL LOGGED IN USER */}
                <div>
                  <h1 className={`text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    Hello {user.name || 'User'}
                  </h1>
                  <p className={`text-xs font-semibold mt-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
                    Monitor real-time business telemetry and rule insights.
                  </p>
                </div>

                {/* 3 HIGHLIGHT METRIC CARDS */}
                <KPICards
                  revenue={analytics?.revenue || 0}
                  orders={analytics?.orders || 0}
                  profitMargin={analytics?.profitMargin || 0}
                  isDarkMode={isDarkMode}
                />

                {/* TREND CHART */}
                <div
                  className={`p-5 rounded-[24px] border shadow-sm ${
                    isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200'
                  }`}
                >
                  <TrendChart
                    isDarkMode={isDarkMode}
                    data={analytics?.trendData || []}
                    summary={analytics?.trendSummary || '$0'}
                    badge={analytics?.trendBadge || 'No active stream'}
                    subtext="Total revenue recorded"
                  />
                </div>

                {/* PERFORMANCE & TELEMETRY TABLE */}
                <div
                  className={`p-5 rounded-[24px] border shadow-sm ${
                    isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200'
                  }`}
                >
                  <PerformanceTable
                    activities={analytics?.activities || []}
                    isDarkMode={isDarkMode}
                  />
                </div>

              </div>

              {/* RIGHT 4 COLUMNS: DATASET INGESTION & RULE-BASED INSIGHTS */}
              <div className="xl:col-span-4 space-y-5">
                
                {/* DATASET INGESTION PANEL */}
                <div
                  className={`p-5 rounded-[24px] border shadow-sm space-y-4 ${
                    isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Database size={18} className="text-[#10b981]" />
                      <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                        Dataset Ingestion
                      </h3>
                    </div>
                    {analytics && (
                      <button
                        onClick={handleResetData}
                        title="Clear active dataset"
                        className="text-xs font-semibold text-rose-500 hover:text-rose-400 transition-colors flex items-center gap-1 cursor-pointer focus:outline-none"
                      >
                        <Trash2 size={13} />
                        <span>Clear</span>
                      </button>
                    )}
                  </div>

                  {/* Status Indicator */}
                  <div className={`p-3 rounded-xl border text-xs ${
                    isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'
                  }`}>
                    {analytics ? (
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                          <CheckCircle2 size={14} />
                          <span>Active Dataset</span>
                        </div>
                        <p className={`text-[11px] font-medium ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                          <span className={`font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>{analytics.fileName}</span> ({analytics.recordsCount} rows)
                        </p>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <AlertCircle size={14} />
                        <span>No dataset ingested. Upload CSV to begin.</span>
                      </div>
                    )}
                  </div>

                  {/* Feedback Notification */}
                  {uploadFeedback && (
                    <div
                      className={`p-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 ${
                        uploadFeedback.type === 'success'
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'
                          : 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20'
                      }`}
                    >
                      {uploadFeedback.type === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                      <span>{uploadFeedback.message}</span>
                    </div>
                  )}

                  {/* Upload Button */}
                  <div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".csv"
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isProcessing}
                      className="w-full py-2.5 px-4 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-sm hover:shadow focus:outline-none"
                    >
                      <Upload size={14} />
                      <span>{isProcessing ? 'Processing...' : 'Upload Sales CSV'}</span>
                    </button>
                  </div>
                </div>

                {/* RULE-BASED STRATEGIC INSIGHTS PREVIEW */}
                <div
                  className={`p-5 rounded-[24px] border shadow-sm ${
                    isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200'
                  }`}
                >
                  <InsightsList
                    insights={analytics?.insights || []}
                    isDarkMode={isDarkMode}
                  />
                </div>

              </div>

            </div>
          )}

          {activeTab === 'Insights' && (
            <InsightsView
              analytics={analytics}
              isDarkMode={isDarkMode}
              onNavigateToUpload={() => handleTabChange('Dashboard')}
            />
          )}

          {activeTab === 'Reports' && (
            <ReportsView
              analytics={analytics}
              isDarkMode={isDarkMode}
              onNavigateToUpload={() => handleTabChange('Dashboard')}
            />
          )}

          {activeTab === 'Documents' && (
            <DocumentsView
              analytics={analytics}
              isDarkMode={isDarkMode}
              onUploadFile={handleFileChange}
              onClearDocument={handleResetData}
              isProcessing={isProcessing}
            />
          )}

          {activeTab === 'Settings' && (
            <SettingsView
              user={user}
              onUpdateUser={handleUpdateUser}
              isDarkMode={isDarkMode}
              onToggleDarkMode={handleToggleTheme}
            />
          )}

        </div>

      </div>

      {/* FLOATING CIRCULAR AI CHATBOT COPILOT */}
      <ChatWidget
        isDarkMode={isDarkMode}
        userName={user.name || 'User'}
        onSendMessage={handleSendChat}
      />

      {/* PROFESSIONAL PROFILE MODAL */}
      {isProfileOpen && (
        <ProfileModal
          user={user}
          onClose={() => setIsProfileOpen(false)}
          onUpdateUser={handleUpdateUser}
          isDarkMode={isDarkMode}
        />
      )}
    </div>
  );
}