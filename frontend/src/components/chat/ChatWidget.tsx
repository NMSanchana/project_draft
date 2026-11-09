'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  X,
  Bot,
  User,
  RotateCcw,
  Paperclip,
  Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatMessage, ChatWidgetProps } from '@/types/chat/chat';
import { uploadKnowledgeDoc } from '@/lib/aiClient';

export function ChatWidget({
  isDarkMode = false,
  userName = 'User',
  onSendMessage,
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const initialGreeting: ChatMessage = {
    id: 'msg-welcome',
    sender: 'assistant',
    text: `Hello ${userName}! 👋 I am your AI Business Analyst. Ask me anything about your revenue metrics, customer trends, or dataset records.`,
    timestamp: 'Just now',
  };

  const [messages, setMessages] = useState<ChatMessage[]>([initialGreeting]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isTyping) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      if (onSendMessage) {
        const responseText = await onSendMessage(text);
        if (responseText) {
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              sender: 'assistant',
              text: responseText,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }
      } else {
        // Interactive simulation for AI developer to connect backend model
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              sender: 'assistant',
              text: `Analyzing: "${text}". Your AI developer can pipe real model responses directly to this component.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
          setIsTyping(false);
        }, 600);
        return;
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-err-${Date.now()}`,
          sender: 'assistant',
          text: 'Unable to reach the AI analytics service. Please try again.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const addAssistantMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `ai-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sender: 'assistant',
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleAttach = async (files: FileList | null) => {
    if (!files || files.length === 0 || isUploading) return;
    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        const lower = file.name.toLowerCase();
        if (!['.pdf', '.txt', '.md'].some((ext) => lower.endsWith(ext))) {
          addAssistantMessage(`"${file.name}" isn't supported here. Attach a PDF, TXT or MD file.`);
          continue;
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `usr-file-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            sender: 'user',
            text: `📎 ${file.name}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
        try {
          await uploadKnowledgeDoc(file);
          addAssistantMessage(`I've read "${file.name}". Go ahead and ask me anything about it.`);
        } catch (e: any) {
          addAssistantMessage(`I couldn't add "${file.name}": ${e?.message || 'upload failed.'}`);
        }
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleClearChat = () => {
    setMessages([initialGreeting]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* PERFECT CIRCULAR FLOATING LAUNCHER BUTTON */}
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? 'Close AI Assistant' : 'Open InsightFlow AI Assistant'}
          className={`w-13 h-13 rounded-full flex items-center justify-center text-white shadow-2xl transition-transform duration-200 cursor-pointer hover:scale-110 active:scale-95 focus:outline-none ${
            isOpen
              ? 'bg-[#0f172a] hover:bg-black ring-2 ring-slate-400/40'
              : 'bg-[#0d2a20] hover:bg-[#143d2f] ring-2 ring-[#10b981]/50 shadow-emerald-950/40'
          }`}
        >
          {isOpen ? (
            <X size={20} className="transition-transform rotate-0 hover:rotate-90" />
          ) : (
            <div className="relative flex items-center justify-center">
              <Sparkles size={20} className="text-[#10b981] transition-transform group-hover:scale-110" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-[#0d2a20] animate-pulse" />
            </div>
          )}
        </button>
      </div>

      {/* SLEEK, COOL, COMPACT CHATBOX PANEL */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.94 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            onDragOver={(e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); handleAttach(e.dataTransfer.files); }}
            className={`fixed bottom-22 right-6 z-50 w-[350px] sm:w-[380px] h-[490px] max-h-[80vh] rounded-[26px] border shadow-2xl flex flex-col overflow-hidden backdrop-blur-md ${
              isDragging ? 'ring-2 ring-[#10b981]' : ''
            } ${
              isDarkMode
                ? 'bg-[#0e1523]/98 border-[#1a2436] text-white shadow-black/80'
                : 'bg-white/98 border-slate-200 text-[#0f172a] shadow-xl'
            }`}
          >
            {/* COMPACT SLEEK HEADER */}
            <div
              className={`px-4 py-3 border-b flex items-center justify-between shrink-0 ${
                isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-[#f8fafc] border-slate-200'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-[#0d2a20] text-[#10b981] flex items-center justify-center shadow-xs">
                  <Bot size={16} />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <h3 className={`text-xs font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                      InsightFlow AI
                    </h3>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  </div>
                  <p className="text-[10px] text-slate-400 font-medium">
                    Copilot Active
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={handleClearChat}
                  title="Reset conversation"
                  className="p-1.5 rounded-lg hover:bg-slate-200/50 dark:hover:bg-white/10 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
                >
                  <RotateCcw size={13} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  title="Close"
                  className="p-1.5 rounded-lg hover:bg-slate-200/50 dark:hover:bg-white/10 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* CUSTOMIZED THIN SCROLLBAR MESSAGE AREA */}
            <div className="flex-1 p-3.5 overflow-y-auto space-y-3 custom-scrollbar text-xs">
              {messages.map((msg) => {
                const isAi = msg.sender === 'assistant';
                return (
                  <div
                    key={msg.id}
                    className={`flex items-end gap-2 ${isAi ? 'justify-start' : 'justify-end'}`}
                  >
                    {isAi && (
                      <div className="w-6 h-6 rounded-full bg-[#0d2a20] text-[#10b981] flex items-center justify-center shrink-0 mb-1">
                        <Sparkles size={11} />
                      </div>
                    )}

                    <div
                      className={`max-w-[82%] px-3.5 py-2.5 leading-relaxed text-[11px] ${
                        isAi
                          ? isDarkMode
                            ? 'bg-[#151d2c] text-slate-100 border border-[#222f46] rounded-2xl rounded-bl-xs'
                            : 'bg-slate-100 text-[#0f172a] rounded-2xl rounded-bl-xs'
                          : 'bg-[#0d2a20] text-white rounded-2xl rounded-br-xs shadow-xs border border-[#10b981]/20'
                      }`}
                    >
                      <p>{msg.text}</p>
                      <span className="block text-[8px] opacity-60 text-right mt-1">
                        {msg.timestamp}
                      </span>
                    </div>

                    {!isAi && (
                      <div className="w-6 h-6 rounded-full bg-[#0f172a] text-white flex items-center justify-center shrink-0 mb-1 text-[10px] font-bold">
                        {userName ? userName.charAt(0).toUpperCase() : <User size={10} />}
                      </div>
                    )}
                  </div>
                );
              })}

              {isTyping && (
                <div className="flex items-center gap-1.5 text-slate-400 text-xs italic pl-8">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.18s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.36s]" />
                  <span className="text-[10px] ml-1">AI analyzing...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* NEAT & CLEAN INPUT FOOTER (NO PREDEFINED QUESTIONS) */}
            <div
              className={`p-3 border-t shrink-0 ${
                isDarkMode ? 'bg-[#080c14] border-[#1a2436]' : 'bg-[#f8fafc] border-slate-200'
              }`}
            >
              <div className="relative flex items-center">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.md"
                  multiple
                  className="hidden"
                  onChange={(e) => handleAttach(e.target.files)}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  title="Attach a PDF, TXT or MD document"
                  className="absolute left-1.5 p-1.5 rounded-lg text-slate-400 hover:text-[#10b981] transition-colors cursor-pointer focus:outline-none disabled:cursor-not-allowed"
                >
                  {isUploading ? <Loader2 size={14} className="animate-spin" /> : <Paperclip size={14} />}
                </button>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isUploading ? "Reading your document..." : "Ask about your data or documents..."}
                  className={`w-full py-2.5 pl-9 pr-10 rounded-xl border text-xs font-semibold focus:outline-none focus:border-[#10b981] ${
                    isDarkMode
                      ? 'bg-[#0e1523] border-[#1a2436] text-white placeholder-slate-500'
                      : 'bg-white border-slate-200 text-[#0f172a] placeholder-slate-400'
                  }`}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isTyping}
                  className={`absolute right-1.5 p-1.5 rounded-lg text-white cursor-pointer focus:outline-none ${
                    input.trim() && !isTyping
                      ? 'bg-[#0d2a20] hover:bg-[#143d2f] scale-100'
                      : 'bg-slate-400 dark:bg-slate-700 opacity-40 cursor-not-allowed'
                  }`}
                >
                  <Send size={12} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}