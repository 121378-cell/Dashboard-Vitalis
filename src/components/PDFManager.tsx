import React, { useCallback } from 'react';
import { FileText, Upload, X, Loader2, Trash2 } from 'lucide-react';
import { PDFDocument } from '../types';

interface Props {
  documents: PDFDocument[];
  onUpload: (file: File) => void;
  onDelete: (id: string) => void;
}

export const PDFManager: React.FC<Props> = ({ documents, onUpload, onDelete }) => {
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      onUpload(file);
    }
  }, [onUpload]);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      onUpload(file);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <h2 className="text-2xl font-headline font-bold">Base de Conocimiento</h2>
      
      {/* REQ-F26: Drag & Drop Zone */}
      <div 
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="border-2 border-dashed border-outline-variant/30 rounded-xl p-12 text-center hover:border-primary/50 transition-all group cursor-pointer relative"
      >
        <input 
          type="file" 
          accept="application/pdf" 
          onChange={onFileSelect}
          className="absolute inset-0 opacity-0 cursor-pointer"
        />
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center text-on-surface-variant group-hover:text-primary transition-colors">
            <Upload size={32} />
          </div>
          <div>
            <p className="font-bold">Arrastra tus PDFs aquí o haz clic para subir</p>
            <p className="text-xs text-on-surface-variant mt-1">Solo archivos PDF de entrenamiento, nutrición o fisiología</p>
          </div>
        </div>
      </div>

      {/* REQ-F30: Document List */}
      <div className="space-y-4">
        {documents.map((doc) => (
          <div key={doc.id} className="bg-surface-container p-4 rounded-xl border border-outline-variant/10 flex gap-4">
            <div className="p-3 bg-primary/10 rounded-lg text-primary h-fit">
              <FileText size={24} />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm">{doc.name}</h4>
                <button 
                  onClick={() => onDelete(doc.id)}
                  className="p-1 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              
              {doc.analyzing ? (
                <div className="flex items-center gap-2 text-[10px] text-primary font-bold uppercase tracking-widest animate-pulse">
                  <Loader2 size={12} className="animate-spin" />
                  Analizando...
                </div>
              ) : (
                <div className="bg-surface-container-low p-3 rounded-lg text-xs text-on-surface-variant leading-relaxed border border-outline-variant/5">
                  <span className="text-[9px] font-bold uppercase text-primary block mb-1">Resumen Técnico</span>
                  {doc.summary}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
