import React from 'react';
import { ProcessedAnalytics } from '@/lib/analytics';

export interface DocumentSchemaColumn {
  name: string;
  type: 'string' | 'number' | 'date';
  sampleValue?: string;
}

export interface IngestedDocumentInfo {
  id: string;
  fileName: string;
  recordCount: number;
  uploadedAt: string;
  columns: DocumentSchemaColumn[];
  fileSizeApprox: string;
}

export interface DocumentsViewProps {
  analytics: ProcessedAnalytics | null;
  isDarkMode: boolean;
  onUploadFile: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onClearDocument: () => void;
  isProcessing: boolean;
}
