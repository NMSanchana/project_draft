'use client';

import React from 'react';
import { Bell, Sun, Moon, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { clearAuthCookieAndStorage } from '@/lib/auth';

interface HeaderBarProps {
  user: { name: string; email: string; avatar?: string };
  onOpenProfile: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
}

export function HeaderBar({
  user,
  onOpenProfile,
  isDarkMode,
  onToggleDarkMode,
}: HeaderBarProps) {
  const router = useRouter();

  const handleLogout = () => {
    clearAuthCookieAndStorage();
    router.push('/en/landing');
  };

  const userInitial = user.name ? user.name.trim().charAt(0).toUpperCase() : 'U';

  return (
    <div className="flex items-center justify-end w-full pb-1">
      {/* RIGHT TOP CONTROLS: DARK MODE TOGGLE, NOTIFICATION, SIGN OUT & PROFESSIONAL USER AVATAR */}
      <div className="flex items-center gap-3">
        
        {/* INSTANT DARK MODE TOGGLE SWITCH (NO OUTLINE POP, NO LAG) */}
        <button
          onClick={onToggleDarkMode}
          title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className={`w-9 h-9 rounded-full border flex items-center justify-center cursor-pointer shadow-sm hover:scale-105 active:scale-95 focus:outline-none ${
            isDarkMode
              ? 'bg-[#151d2c] border-[#222f46] text-amber-400 hover:bg-[#1a2436]'
              : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
          }`}
        >
          {isDarkMode ? (
            <Sun size={17} className="transition-transform rotate-0 hover:rotate-45" />
          ) : (
            <Moon size={17} className="transition-transform rotate-0 hover:-rotate-12" />
          )}
        </button>

        {/* NOTIFICATION BUTTON */}
        <button
          title="Notifications"
          className={`relative w-9 h-9 rounded-full border flex items-center justify-center cursor-pointer shadow-sm hover:scale-105 active:scale-95 focus:outline-none ${
            isDarkMode
              ? 'bg-[#151d2c] border-[#222f46] text-slate-300 hover:bg-[#1a2436]'
              : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
          }`}
        >
          <Bell size={17} />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-[#080c14]" />
        </button>

        {/* SIGN OUT BUTTON */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 hover:bg-red-500 hover:text-white text-xs font-bold transition-all cursor-pointer hover:shadow-xs active:scale-95 focus:outline-none"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Sign Out</span>
        </button>

        {/* PROFESSIONAL USER AVATAR */}
        <button
          onClick={onOpenProfile}
          title="Profile Settings & Photo"
          className="relative group cursor-pointer focus:outline-none ml-1 rounded-full transition-transform hover:scale-105"
        >
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.name || 'User'}
              className="w-9 h-9 rounded-full object-cover border-2 border-white dark:border-[#151d2c] ring-2 ring-slate-200 dark:ring-[#1a2436] group-hover:ring-[#10b981] shadow-sm"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-[#0d2a20] border-2 border-white dark:border-[#151d2c] ring-2 ring-slate-200 dark:ring-[#1a2436] group-hover:ring-[#10b981] text-white flex items-center justify-center text-xs font-extrabold shadow-sm">
              {userInitial}
            </div>
          )}
        </button>

      </div>
    </div>
  );
}
