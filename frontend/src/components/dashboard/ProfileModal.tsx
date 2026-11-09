'use client';

import React, { useState, useRef } from 'react';
import { X, Camera, Trash2, User, AlertCircle, CheckCircle2, Upload } from 'lucide-react';
import { motion } from 'framer-motion';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

interface ProfileModalProps {
  user: { id?: string; name: string; email: string; avatar?: string };
  onClose: () => void;
  onUpdateUser: (updatedUser: { id?: string; name: string; email: string; avatar?: string }) => void;
  isDarkMode?: boolean;
}

export function ProfileModal({ user, onClose, onUpdateUser, isDarkMode = false }: ProfileModalProps) {
  const [name, setName] = useState(user.name);
  const [avatar, setAvatar] = useState(user.avatar || '');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setFeedback({ type: 'error', message: 'Name cannot be empty.' });
      return;
    }

    setLoading(true);
    setFeedback(null);

    const updated = {
      ...user,
      name: name.trim(),
      avatar: avatar,
    };

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${BACKEND_URL}/api/auth/profile`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          name: updated.name,
          avatar: updated.avatar,
        }),
      });

      if (res.status === 401) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
        throw new Error('Your session has expired. Please sign in again.');
      }

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || 'Failed to update profile.');
      }

      const savedUser = data.user || updated;
      if (typeof window !== 'undefined') {
        localStorage.setItem('user', JSON.stringify(savedUser));
      }

      onUpdateUser(savedUser);
      setFeedback({ type: 'success', message: 'Profile updated successfully!' });
      
      setTimeout(() => {
        onClose();
      }, 700);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Unable to update profile.' });
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setFeedback({ type: 'error', message: 'Please select a valid image file (PNG, JPG, or WEBP).' });
      return;
    }

    // Max 4MB size
    if (file.size > 4 * 1024 * 1024) {
      setFeedback({ type: 'error', message: 'Image size must be under 4MB.' });
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      if (typeof event.target?.result === 'string') {
        setAvatar(event.target.result);
        setFeedback(null);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = () => {
    setAvatar('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const initial = (name || user.name || 'U').trim().charAt(0).toUpperCase();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className={`rounded-3xl p-6 lg:p-8 max-w-md w-full shadow-2xl relative space-y-6 border ${
          isDarkMode
            ? 'bg-[#0e1523] border-[#1a2436] text-white'
            : 'bg-white border-slate-200 text-[#0f172a]'
        }`}
      >
        {/* CLOSE BUTTON */}
        <button
          onClick={onClose}
          className={`absolute top-6 right-6 transition-colors cursor-pointer focus:outline-none ${
            isDarkMode ? 'text-slate-400 hover:text-white' : 'text-slate-400 hover:text-[#0f172a]'
          }`}
        >
          <X size={20} />
        </button>

        {/* HEADER */}
        <div>
          <h3 className={`text-2xl font-extrabold tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
            Edit Profile
          </h3>
          <p className={`text-xs font-medium mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
            Update your display name and upload a professional profile photo.
          </p>
        </div>

        {/* FEEDBACK NOTIFICATION */}
        {feedback && (
          <div
            className={`p-3 rounded-2xl text-xs font-semibold flex items-center gap-2 ${
              feedback.type === 'success'
                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'
                : 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400 border border-red-200 dark:border-red-500/20'
            }`}
          >
            {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* PROFESSIONAL PHOTO UPLOAD SECTION */}
        <div className="flex flex-col items-center space-y-3 py-1">
          <div className="relative group">
            {avatar ? (
              <img
                src={avatar}
                alt="Profile Preview"
                className="w-24 h-24 rounded-full object-cover border-4 border-white dark:border-[#1a2436] shadow-md ring-2 ring-slate-200 dark:ring-slate-700"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-[#0d2a20] text-white flex items-center justify-center text-3xl font-extrabold border-4 border-white dark:border-[#1a2436] shadow-md ring-2 ring-slate-200 dark:ring-slate-700">
                {initial}
              </div>
            )}

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Change photo"
              className="absolute bottom-0 right-0 p-2 rounded-full bg-[#0f172a] hover:bg-black text-white shadow-md transition-all cursor-pointer ring-2 ring-white focus:outline-none"
            >
              <Camera size={14} />
            </button>
          </div>

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handlePhotoSelect}
            accept="image/png, image/jpeg, image/webp"
            className="hidden"
          />

          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={`px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 cursor-pointer focus:outline-none ${
                isDarkMode
                  ? 'border-slate-700 hover:bg-white/5 text-slate-200'
                  : 'border-slate-200 hover:bg-slate-50 text-slate-700'
              }`}
            >
              <Upload size={13} />
              <span>Upload Photo</span>
            </button>

            {avatar && (
              <button
                type="button"
                onClick={handleRemovePhoto}
                className="px-3 py-1.5 rounded-xl border border-rose-200 dark:border-rose-500/20 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-xs font-bold text-rose-500 flex items-center gap-1.5 cursor-pointer focus:outline-none"
              >
                <Trash2 size={13} />
                <span>Remove</span>
              </button>
            )}
          </div>
        </div>

        {/* NAME INPUT */}
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-1.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your Name"
              className={`w-full rounded-2xl py-3 pl-10 pr-4 text-sm font-semibold border focus:outline-none focus:border-[#10b981] ${
                isDarkMode
                  ? 'bg-[#080c14] border-[#1a2436] text-white placeholder-slate-500'
                  : 'bg-slate-50 border-slate-200 text-[#0f172a] placeholder-slate-400'
              }`}
            />
          </div>
        </div>

        {/* EMAIL (READ-ONLY) */}
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-1.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
            Verified Account Email
          </label>
          <input
            type="text"
            value={user.email}
            disabled
            className={`w-full rounded-2xl py-3 px-4 text-xs font-semibold border cursor-not-allowed opacity-80 ${
              isDarkMode
                ? 'bg-[#080c14] border-[#1a2436] text-slate-400'
                : 'bg-slate-100 border-slate-200 text-slate-500'
            }`}
          />
        </div>

        {/* SAVE ACTION */}
        <button
          onClick={handleSave}
          disabled={loading}
          className="w-full py-3.5 px-6 rounded-2xl bg-[#0d2a20] hover:bg-[#143d2f] text-white font-bold text-sm shadow-md transition-all cursor-pointer flex items-center justify-center gap-2 focus:outline-none"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <span>Save Profile</span>
          )}
        </button>

      </motion.div>
    </div>
  );
}
