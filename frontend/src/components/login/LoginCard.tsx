'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { setAuthCookieAndStorage } from '@/lib/auth';

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'http://localhost:5000';

/**
 * Clean, professional InsightFlow logo mark
 */
function InsightFlowLogo({ isDark = true }: { isDark?: boolean }) {
  return (
    <div className="flex items-center gap-3 group cursor-pointer select-none">
      <div className="w-9 h-9 rounded-xl bg-[#54bd95] flex items-center justify-center text-[#0d1f19] transition-transform duration-200 group-hover:scale-105 shrink-0">
        <svg
          className="w-5 h-5 text-[#0d1f19]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
          <polyline points="16 7 22 7 22 13" />
        </svg>
      </div>

      <span className={`text-2xl font-bold tracking-tight ${isDark ? 'text-white' : 'text-[#0d2a20]'}`}>
        Insight<span className="text-[#54bd95]">Flow</span>
      </span>
    </div>
  );
}

export function LoginCard() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Form inputs
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Status feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Auto-scroll references
  const rightPanelRef = useRef<HTMLDivElement>(null);
  const formEndRef = useRef<HTMLDivElement>(null);

  // Smooth auto-scroll when toggling Sign In / Sign Up
  const handleTabSwitch = (loginState: boolean) => {
    setIsLogin(loginState);
    setError('');
    setSuccessMsg('');

    setTimeout(() => {
      if (!loginState) {
        // Switched to Sign Up: scroll down so full form and action buttons are fully in view
        if (formEndRef.current) {
          formEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        if (rightPanelRef.current) {
          rightPanelRef.current.scrollTo({
            top: rightPanelRef.current.scrollHeight,
            behavior: 'smooth',
          });
        }
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: 'smooth',
        });
      } else {
        // Switched to Sign In: scroll smoothly back up
        if (rightPanelRef.current) {
          rightPanelRef.current.scrollTo({
            top: 0,
            behavior: 'smooth',
          });
        }
        window.scrollTo({
          top: 0,
          behavior: 'smooth',
        });
      }
    }, 120);
  };

  // Additional observer to make sure when fields animate into DOM, bottom stays visible
  useEffect(() => {
    if (!isLogin) {
      const timer = setTimeout(() => {
        if (formEndRef.current) {
          formEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
      }, 240);
      return () => clearTimeout(timer);
    }
  }, [isLogin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!isLogin) {
      if (!name.trim()) {
        setError('Please enter your full name');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters');
        return;
      }
    }

    if (!email || !password) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);

    try {
      const endpoint = isLogin
        ? `${BACKEND_URL}/api/auth/login`
        : `${BACKEND_URL}/api/auth/register`;
      const payload = isLogin ? { email, password } : { name, email, password };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.message || 'Authentication failed');
      }

      // Store Session in 1-day cookie & storage
      if (data.token) {
        setAuthCookieAndStorage(data.token, data.user);
      }

      setSuccessMsg(data.message || 'Success! Redirecting to dashboard...');

      setTimeout(() => {
        router.push('/en/dashboard');
      }, 700);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to authentication server.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Google User',
          email: 'user.google@gmail.com',
          avatar:
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=250&q=80',
        }),
      });
      const data = await res.json();
      if (data.success) {
        if (data.token) {
          setAuthCookieAndStorage(data.token, data.user);
        }
        setSuccessMsg('Google Authentication Successful!');
        setTimeout(() => router.push('/en/dashboard'), 700);
      } else {
        throw new Error(data.message || 'Google Sign In failed');
      }
    } catch (err: any) {
      setError(err.message || 'Google Sign In failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#fafbfa] text-[#191a15] font-sans selection:bg-[#54bd95] selection:text-white">
      
      {/* ========================================================= */}
      {/* LEFT 50%: BRAND PANEL WITH NEAT LOGO AT TOP-LEFT          */}
      {/* ========================================================= */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex w-full lg:w-1/2 bg-[#0d1f19] text-white flex-col justify-between p-8 sm:p-12 lg:p-16 shrink-0 min-h-screen"
      >
        {/* Top-Left: Clean Modern Logo */}
        <div>
          <Link
            href="/en/landing"
            className="inline-flex items-center gap-3 group"
          >
            <InsightFlowLogo isDark={true} />
          </Link>
        </div>

        {/* Center: Minimalist Headline & Description */}
        <div className="my-auto py-8 max-w-md">
          <h1 className="text-3xl sm:text-4xl font-semibold text-white tracking-tight leading-snug mb-3">
            Simpler analytics for smarter business decisions.
          </h1>
          <p className="text-emerald-100/70 text-base leading-relaxed">
            Consolidate your metrics, monitor performance in real time, and scale with clarity.
          </p>
        </div>

        {/* Bottom: Subtle Copyright */}
        <div className="text-xs text-emerald-100/40">
          © {new Date().getFullYear()} InsightFlow Inc. All rights reserved.
        </div>
      </motion.div>

      {/* ========================================================= */}
      {/* RIGHT 50%: AUTHENTICATION FORM PANEL                       */}
      {/* ========================================================= */}
      <motion.div
        ref={rightPanelRef}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-10 lg:p-12 lg:py-8 bg-white overflow-y-auto scroll-smooth min-h-screen"
      >
        {/* Top Bar Navigation */}
        <div className="flex items-center justify-end mb-6 sm:mb-8 w-full">
          <Link
            href="/en/landing"
            className="inline-flex items-center gap-2 text-xs font-bold text-gray-600 hover:text-[#0d2a20] px-4 py-2 rounded-full border border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50 transition-all shadow-sm hover:shadow shrink-0 cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back to website</span>
          </Link>
        </div>

        {/* Centered Form Wrapper */}
        <div className="w-full max-w-[420px] mx-auto my-auto py-2">
          {/* Header Title */}
          <div className="mb-6">
            <h2 className="text-3xl font-extrabold text-[#191a15] tracking-tight mb-2">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="text-gray-500 text-sm">
              {isLogin
                ? 'Enter your credentials to access your analytics dashboard.'
                : 'Start your high-performance business intelligence journey today.'}
            </p>
          </div>

          {/* Clean Segmented Tab Switcher */}
          <div className="grid grid-cols-2 p-1 bg-gray-100 rounded-xl mb-6 border border-gray-200/80">
            <button
              type="button"
              onClick={() => handleTabSwitch(true)}
              className={`py-2 text-sm font-bold rounded-lg transition-all cursor-pointer ${
                isLogin
                  ? 'bg-white text-[#0d2a20] shadow-sm'
                  : 'text-gray-500 hover:text-[#191a15]'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleTabSwitch(false)}
              className={`py-2 text-sm font-bold rounded-lg transition-all cursor-pointer ${
                !isLogin
                  ? 'bg-white text-[#0d2a20] shadow-sm'
                  : 'text-gray-500 hover:text-[#191a15]'
              }`}
            >
              Sign Up
            </button>
          </div>

          {/* Notifications */}
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                key="error-box"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="flex items-start gap-3 p-3.5 mb-5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-medium"
              >
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </motion.div>
            )}

            {successMsg && (
              <motion.div
                key="success-box"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="flex items-start gap-3 p-3.5 mb-5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium"
              >
                <CheckCircle2 size={18} className="shrink-0 mt-0.5 text-emerald-600" />
                <span>{successMsg}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ========================================================= */}
          {/* 1. CREDENTIALS FORM FIRST (EMAIL & PASSWORDS FIRST)        */}
          {/* ========================================================= */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name (Sign Up only) */}
            <AnimatePresence mode="popLayout">
              {!isLogin && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                      type="text"
                      required={!isLogin}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full bg-white border border-gray-200 rounded-xl py-3 pl-10 pr-4 text-[#191a15] text-sm placeholder-gray-400 focus:outline-none focus:border-[#0d2a20] focus:ring-2 focus:ring-[#0d2a20]/10 transition-all"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full bg-white border border-gray-200 rounded-xl py-3 pl-10 pr-4 text-[#191a15] text-sm placeholder-gray-400 focus:outline-none focus:border-[#0d2a20] focus:ring-2 focus:ring-[#0d2a20]/10 transition-all"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Password
                </label>
                {isLogin && (
                  <button
                    type="button"
                    onClick={() => setError('Password reset instructions sent to your email.')}
                    className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition-colors cursor-pointer"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white border border-gray-200 rounded-xl py-3 pl-10 pr-10 text-[#191a15] text-sm placeholder-gray-400 focus:outline-none focus:border-[#0d2a20] focus:ring-2 focus:ring-[#0d2a20]/10 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-colors p-1 cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Confirm Password (Sign Up only) */}
            <AnimatePresence mode="popLayout">
              {!isLogin && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required={!isLogin}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-white border border-gray-200 rounded-xl py-3 pl-10 pr-4 text-[#191a15] text-sm placeholder-gray-400 focus:outline-none focus:border-[#0d2a20] focus:ring-2 focus:ring-[#0d2a20]/10 transition-all"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Remember Me Checkbox (Login mode) */}
            {isLogin && (
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="rememberMe"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-[#0d2a20] focus:ring-[#0d2a20] cursor-pointer"
                />
                <label
                  htmlFor="rememberMe"
                  className="text-xs font-medium text-gray-600 select-none cursor-pointer"
                >
                  Remember me on this device
                </label>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 px-6 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 group disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>{isLogin ? 'Sign In to Dashboard' : 'Create InsightFlow Account'}</span>
                  <ArrowRight
                    size={16}
                    className="group-hover:translate-x-1 transition-transform"
                  />
                </>
              )}
            </button>
          </form>

          {/* ========================================================= */}
          {/* 2. SUBTLE DIVIDER (NO "CONTINUE WITH EMAIL" LABEL TEXT)    */}
          {/* ========================================================= */}
          <div className="relative flex items-center my-5">
            <div className="flex-grow border-t border-gray-200" />
            <span className="shrink-0 mx-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              or
            </span>
            <div className="flex-grow border-t border-gray-200" />
          </div>

          {/* ========================================================= */}
          {/* 3. GOOGLE SIGN IN BUTTON BELOW                            */}
          {/* ========================================================= */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border border-gray-200 bg-white hover:bg-gray-50/90 text-gray-700 font-semibold text-sm shadow-sm hover:border-gray-300 transition-all disabled:opacity-60 cursor-pointer"
          >
            <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 10.8 0 12.5s.7 2.8 1.9 5.2l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

          {/* Toggle footer info */}
          <div className="mt-5 text-center text-xs text-gray-500">
            {isLogin ? (
              <span>
                Don&apos;t have an account yet?{' '}
                <button
                  type="button"
                  onClick={() => handleTabSwitch(false)}
                  className="font-bold text-[#0d2a20] hover:underline cursor-pointer"
                >
                  Sign up for free
                </button>
              </span>
            ) : (
              <span>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleTabSwitch(true)}
                  className="font-bold text-[#0d2a20] hover:underline cursor-pointer"
                >
                  Sign in
                </button>
              </span>
            )}
          </div>

          {/* Auto-scroll target marker to keep all action buttons visible */}
          <div ref={formEndRef} className="h-4" />
        </div>
      </motion.div>

    </div>
  );
}
