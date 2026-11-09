'use client';

import React, { useRef, useState } from 'react';
import {
  FileCode,
  Upload,
  Trash2,
  FileSpreadsheet,
  CheckCircle2,
  File,
  Plus,
  Clock,
} from 'lucide-react';
import { DocumentsViewProps } from '@/types/documents/documents';
import { KnowledgeDocuments } from './KnowledgeDocuments';

export function DocumentsView({
  analytics,
  isDarkMode,
  onUploadFile,
  onClearDocument,
  isProcessing,
}: DocumentsViewProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const fakeEvent = {
        target: { files: e.dataTransfer.files },
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      onUploadFile(fakeEvent);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-between space-y-6 min-h-[720px]">
      <div className="space-y-6">
        {/* HEADER SECTION */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <FileCode className="text-[#10b981]" size={22} />
              <h1 className={`text-2xl lg:text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                Document Repository
              </h1>
            </div>
            <p className={`text-xs font-semibold mt-1 ${isDarkMode ? 'text-slate-300' : 'text-slate-500'}`}>
              Manage your sales datasets (CSV, XLSX, JSON) and the PDF documents the chat can answer from.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={onUploadFile}
              accept=".csv,.xlsx,.json"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing}
              className="px-4 py-2.5 rounded-xl bg-[#0d2a20] hover:bg-[#143d2f] text-white text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-sm hover:shadow focus:outline-none"
            >
              <Plus size={15} />
              <span>{isProcessing ? 'Processing...' : 'Upload Document'}</span>
            </button>
          </div>
        </div>

        {/* DRAG AND DROP ZONE */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`p-8 rounded-[24px] border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center text-center space-y-3 focus:outline-none ${
            isDragging
              ? 'border-[#10b981] bg-emerald-500/5 scale-[1.005]'
              : isDarkMode
              ? 'bg-[#080c14] border-[#1a2436] hover:bg-[#0e1523] hover:border-slate-500'
              : 'bg-white border-slate-200 hover:bg-slate-50/60 hover:border-slate-300 shadow-xs'
          }`}
        >
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-[#10b981] flex items-center justify-center">
            <Upload size={22} />
          </div>
          <div className="space-y-0.5">
            <p className={`text-sm font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
              Drag & drop your dataset file here, or <span className="text-[#10b981] underline underline-offset-2">browse files</span>
            </p>
            <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Supports CSV, XLSX, and JSON formatted business records
            </p>
          </div>
        </div>

        {/* DOCUMENTS TABLE */}
        <div
          className={`p-6 rounded-[24px] border space-y-4 ${
            isDarkMode ? 'bg-[#0e1523] border-[#1a2436]' : 'bg-white border-slate-200 shadow-sm'
          }`}
        >
          <div className={`flex items-center justify-between border-b pb-3 ${isDarkMode ? 'border-[#1a2436]' : 'border-slate-200'}`}>
            <h3 className={`text-sm font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
              Uploaded Business Files
            </h3>
            <span className={`text-xs font-medium ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              {analytics ? '1 Active Dataset' : '0 Documents'}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className={`border-b uppercase text-[10px] font-bold tracking-wider ${isDarkMode ? 'border-[#1a2436] text-slate-400' : 'border-slate-200 text-slate-500'}`}>
                  <th className="pb-3 px-3">File Name</th>
                  <th className="pb-3 px-3">Format</th>
                  <th className="pb-3 px-3">Records / Size</th>
                  <th className="pb-3 px-3">Status</th>
                  <th className="pb-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDarkMode ? 'divide-[#1a2436]' : 'divide-slate-200'}`}>
                {analytics ? (
                  <tr className={`transition-colors ${isDarkMode ? 'hover:bg-[#151d2c]' : 'hover:bg-slate-50/50'}`}>
                    <td className="py-3.5 px-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-[#10b981] flex items-center justify-center shrink-0">
                          <FileSpreadsheet size={16} />
                        </div>
                        <div>
                          <p className={`font-bold ${isDarkMode ? 'text-white' : 'text-[#0f172a]'}`}>
                            {analytics.fileName}
                          </p>
                          <p className={`text-[11px] flex items-center gap-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                            <Clock size={11} />
                            <span>Active Ingestion Batch</span>
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className={`py-3.5 px-3 font-semibold uppercase ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      CSV
                    </td>
                    <td className={`py-3.5 px-3 font-semibold ${isDarkMode ? 'text-slate-200' : 'text-slate-700'}`}>
                      {analytics.recordsCount} rows
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                        <CheckCircle2 size={12} />
                        Ingested
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      <button
                        onClick={onClearDocument}
                        title="Remove file"
                        className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer focus:outline-none"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ) : (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isDarkMode ? 'bg-[#151d2c] text-slate-400' : 'bg-slate-100 text-slate-400'}`}>
                          <File size={18} />
                        </div>
                        <p className={`text-xs font-semibold ${isDarkMode ? 'text-slate-200' : 'text-slate-700'}`}>
                          No documents uploaded yet
                        </p>
                        <p className={`text-[11px] max-w-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                          Upload your business spreadsheet above to inspect columns, audit data rows, and manage document storage.
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* KNOWLEDGE DOCUMENTS (PDF / TXT / MD for document Q&A) */}
        <KnowledgeDocuments isDarkMode={isDarkMode} />
      </div>
    </div>
  );
}