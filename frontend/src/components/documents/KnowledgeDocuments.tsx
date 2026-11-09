'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen, Upload, Trash2, FileText, Loader2, CheckCircle2, Users, AlertCircle } from 'lucide-react';
import {
  KnowledgeDoc,
  listKnowledgeDocs,
  uploadKnowledgeDoc,
  deleteKnowledgeDoc,
} from '@/lib/aiClient';

const ALLOWED = ['.pdf', '.txt', '.md'];

export function KnowledgeDocuments({ isDarkMode }: { isDarkMode: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const refresh = useCallback(async () => {
    try {
      setDocs(await listKnowledgeDocs());
    } catch (e: any) {
      setError(e?.message || 'Could not load documents.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setError('');
    setNotice('');
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const lower = file.name.toLowerCase();
        if (!ALLOWED.some((ext) => lower.endsWith(ext))) {
          throw new Error(`"${file.name}" is not supported. Use PDF, TXT or MD files.`);
        }
        await uploadKnowledgeDoc(file);
      }
      setNotice('Document added. You can now ask questions about it in the chat.');
      await refresh();
    } catch (e: any) {
      setError(e?.message || 'Upload failed.');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDelete = async (doc: KnowledgeDoc) => {
    setError('');
    setNotice('');
    try {
      await deleteKnowledgeDoc(doc.id);
      await refresh();
    } catch (e: any) {
      setError(e?.message || 'Could not delete the document.');
    }
  };

  const text = isDarkMode ? 'text-white' : 'text-[#0f172a]';
  const muted = isDarkMode ? 'text-slate-400' : 'text-slate-500';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 pt-2">
        <BookOpen className="text-[#10b981]" size={20} />
        <h2 className={`text-xl font-black tracking-tight ${text}`}>Knowledge Documents</h2>
      </div>
      <p className={`text-xs font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
        Upload PDFs, TXT or Markdown files (policies, contracts, playbooks). Ask about them in the chat and
        answers will cite the file and page.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`p-8 rounded-[24px] border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center text-center space-y-3 ${
          isDragging
            ? 'border-[#10b981] bg-emerald-500/5'
            : isDarkMode
            ? 'bg-[#080c14] border-[#1a2436] hover:bg-[#0e1523]'
            : 'bg-white border-slate-200 hover:bg-slate-50/60 shadow-xs'
        }`}
      >
        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-[#10b981] flex items-center justify-center">
          {uploading ? <Loader2 size={22} className="animate-spin" /> : <Upload size={22} />}
        </div>
        <p className={`text-sm font-bold ${text}`}>
          {uploading ? (
            'Reading and indexing your document... (the first one can take a minute)'
          ) : (
            <>Drag & drop a PDF here, or <span className="text-[#10b981] underline underline-offset-2">browse files</span></>
          )}
        </p>
        <p className={`text-xs ${muted}`}>Supports PDF, TXT and MD</p>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs font-semibold text-rose-500 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2.5">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2.5">
          <CheckCircle2 size={14} />
          <span>{notice}</span>
        </div>
      )}

      <div className={`p-6 rounded-[24px] border space-y-4 ${isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-sm'}`}>
        <div className={`flex items-center justify-between border-b pb-3 ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
          <h3 className={`text-sm font-bold ${text}`}>Documents available to chat</h3>
          <span className={`text-xs font-medium ${muted}`}>{docs.length} document{docs.length === 1 ? '' : 's'}</span>
        </div>

        {loading ? (
          <p className={`text-xs py-6 text-center ${muted}`}>Loading...</p>
        ) : docs.length === 0 ? (
          <p className={`text-xs py-6 text-center ${muted}`}>No documents yet. Upload a PDF above.</p>
        ) : (
          <ul className={`divide-y ${isDarkMode ? 'divide-[#1a2436]' : 'divide-slate-200'}`}>
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-[#10b981] flex items-center justify-center shrink-0">
                    <FileText size={16} />
                  </div>
                  <div className="min-w-0">
                    <p className={`text-xs font-bold truncate ${text}`}>{d.fileName}</p>
                    <p className={`text-[11px] ${muted}`}>{d.chunks} passages indexed</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {d.shared ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-500 bg-sky-500/10 px-2.5 py-1 rounded-full border border-sky-500/20">
                      <Users size={12} /> Shared
                    </span>
                  ) : (
                    <>
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                        <CheckCircle2 size={12} /> Private
                      </span>
                      <button
                        onClick={() => handleDelete(d)}
                        title="Delete document"
                        className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer"
                      >
                        <Trash2 size={14} />
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}