'use client';

import React, { useState, useRef } from 'react';
import {
  Settings,
  User,
  Moon,
  Sun,
  DollarSign,
  Percent,
  CheckCircle2,
  Save,
  Shield,
  Upload,
  Trash2,
} from 'lucide-react';
import { SettingsViewProps, CurrencyCode } from '@/types/settings/settings';
import { CURRENCY_OPTIONS, DEFAULT_PLATFORM_PREFERENCES } from '@/data/settings/settings';

export function SettingsView({
  user,
  onUpdateUser,
  isDarkMode,
  onToggleDarkMode,
}: SettingsViewProps) {
  const [displayName, setDisplayName] = useState(user.name || '');
  const [avatar, setAvatar] = useState(user.avatar || '');
  const [currency, setCurrency] = useState<CurrencyCode>(DEFAULT_PLATFORM_PREFERENCES.currency);
  const [targetMargin, setTargetMargin] = useState(DEFAULT_PLATFORM_PREFERENCES.targetMarginThreshold);
  const [feedback, setFeedback] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSaveProfile = () => {
    onUpdateUser({
      ...user,
      name: displayName,
      avatar: avatar,
    });
    setFeedback('Settings updated successfully!');
    setTimeout(() => setFeedback(null), 3000);
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setFeedback('Please select a valid image file (PNG, JPG, or WEBP).');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      if (typeof event.target?.result === 'string') {
        setAvatar(event.target.result);
        setFeedback('Photo selected. Click "Save Preferences" to apply.');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = () => {
    setAvatar('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    setFeedback('Photo removed. Click "Save Preferences" to apply.');
  };

  const initial = (displayName || user.name || 'U').trim().charAt(0).toUpperCase();

  return (
    <div className="flex-1 flex flex-col justify-between space-y-6 min-h-[720px]">
      <div className="space-y-6">
        {/* HEADER SECTION */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Settings className="text-[#10b981]" size={22} />
              <h1 className={`text-2xl lg:text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                Settings & Preferences
              </h1>
            </div>
            <p className={`text-xs font-semibold mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
              Configure personal profile details and platform business parameters.
            </p>
          </div>

          {feedback && (
            <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <CheckCircle2 size={14} />
              <span>{feedback}</span>
            </div>
          )}
        </div>

        {/* 2 BALANCED EQUAL-HEIGHT CARDS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
          
          {/* CARD 1: USER PROFILE */}
          <div
            className={`p-6 rounded-[24px] border flex flex-col justify-between space-y-6 ${
              isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-sm'
            }`}
          >
            <div className="space-y-5">
              <div className={`flex items-center gap-2 border-b pb-3 ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
                <User size={18} className="text-[#10b981]" />
                <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                  Personal Profile
                </h3>
              </div>

              {/* Photo Upload Row */}
              <div className="flex items-center gap-4">
                <div className="relative group">
                  {avatar ? (
                    <img
                      src={avatar}
                      alt="Profile"
                      className="w-16 h-16 rounded-full object-cover border-2 border-white dark:border-[#1a2436] shadow-md ring-2 ring-slate-200 dark:ring-slate-700"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded-full bg-[#0d2a20] text-white flex items-center justify-center text-xl font-extrabold border-2 border-white dark:border-[#1a2436] shadow-md ring-2 ring-slate-200 dark:ring-slate-700">
                      {initial}
                    </div>
                  )}
                </div>

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handlePhotoSelect}
                  accept="image/png, image/jpeg, image/webp"
                  className="hidden"
                />

                <div className="space-y-1">
                  <p className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    Profile Photo
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors focus:outline-none"
                    >
                      <Upload size={12} />
                      <span>Upload Photo</span>
                    </button>
                    {avatar && (
                      <button
                        type="button"
                        onClick={handleRemovePhoto}
                        className="px-3 py-1.5 rounded-xl border border-rose-200 dark:border-rose-500/20 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-xs font-semibold text-rose-500 cursor-pointer transition-colors focus:outline-none"
                      >
                        <Trash2 size={12} />
                        <span>Remove</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Display Name Input */}
              <div className="space-y-1.5">
                <label className={`text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your full name"
                  className={`w-full px-4 py-2.5 rounded-xl border text-xs font-semibold focus:outline-none focus:border-[#10b981] ${
                    isDarkMode
                      ? 'bg-[#080c14] border-[#1a2436] text-white placeholder-slate-500'
                      : 'bg-slate-50 border-slate-200 text-[#0f172a] placeholder-slate-400'
                  }`}
                />
              </div>

              {/* Verified Email Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className={`text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                    Account Email
                  </label>
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    Verified
                  </span>
                </div>
                <input
                  type="text"
                  value={user.email}
                  disabled
                  className={`w-full px-4 py-2.5 rounded-xl border text-xs font-semibold opacity-75 cursor-not-allowed ${
                    isDarkMode
                      ? 'bg-[#080c14] border-[#1a2436] text-slate-400'
                      : 'bg-slate-100 border-slate-200 text-slate-500'
                  }`}
                />
              </div>
            </div>
          </div>

          {/* CARD 2: SYSTEM & PLATFORM PREFERENCES */}
          <div
            className={`p-6 rounded-[24px] border flex flex-col justify-between space-y-6 ${
              isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-sm'
            }`}
          >
            <div className="space-y-5">
              <div className={`flex items-center gap-2 border-b pb-3 ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
                <Shield size={18} className="text-[#10b981]" />
                <h3 className={`text-base font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                  Platform Preferences
                </h3>
              </div>

              {/* Primary Currency */}
              <div className="space-y-1.5">
                <label className={`text-xs font-bold flex items-center gap-1.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                  <DollarSign size={13} />
                  <span>Primary Currency</span>
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value as CurrencyCode)}
                  className={`w-full px-4 py-2.5 rounded-xl border text-xs font-semibold focus:outline-none focus:border-[#10b981] cursor-pointer ${
                    isDarkMode
                      ? 'bg-[#080c14] border-[#1a2436] text-white'
                      : 'bg-slate-50 border-slate-200 text-[#0f172a]'
                  }`}
                >
                  {CURRENCY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Target Profit Margin Threshold */}
              <div className="space-y-1.5">
                <label className={`text-xs font-bold flex items-center gap-1.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                  <Percent size={13} />
                  <span>Target Profit Margin Threshold (%)</span>
                </label>
                <input
                  type="number"
                  value={targetMargin}
                  onChange={(e) => setTargetMargin(Number(e.target.value))}
                  min={0}
                  max={100}
                  className={`w-full px-4 py-2.5 rounded-xl border text-xs font-semibold focus:outline-none focus:border-[#10b981] ${
                    isDarkMode
                      ? 'bg-[#080c14] border-[#1a2436] text-white'
                      : 'bg-slate-50 border-slate-200 text-[#0f172a]'
                  }`}
                />
                <p className={`text-[10px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Analytics engine flags performance below this threshold as margin alerts.
                </p>
              </div>

              {/* Appearance Mode */}
              <div className="space-y-1.5 pt-1">
                <label className={`text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                  Appearance Theme
                </label>
                <div className={`flex items-center justify-between p-3 rounded-xl border ${
                  isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className={`text-xs font-semibold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                    {isDarkMode ? 'Dark Mode' : 'Light Mode'}
                  </span>
                  <button
                    type="button"
                    onClick={onToggleDarkMode}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 cursor-pointer focus:outline-none ${
                      isDarkMode
                        ? 'bg-[#151d2c] border-[#222f46] text-amber-400 hover:bg-[#1a2436]'
                        : 'bg-white border-slate-200 text-slate-700 shadow-2xs hover:bg-slate-50'
                    }`}
                  >
                    {isDarkMode ? <Sun size={14} /> : <Moon size={14} />}
                    <span>Switch to {isDarkMode ? 'Light' : 'Dark'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* BOTTOM ACTION BAR */}
      <div className={`pt-4 border-t flex justify-end ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
        <button
          onClick={handleSaveProfile}
          className="px-6 py-3 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white font-bold text-xs flex items-center gap-2 cursor-pointer shadow-sm hover:shadow focus:outline-none"
        >
          <Save size={14} />
          <span>Save Preferences</span>
        </button>
      </div>
    </div>
  );
}
