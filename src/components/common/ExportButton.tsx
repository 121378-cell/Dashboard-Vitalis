import React from 'react';
import { Button } from '../ui/button';
import { Download, Share2 } from 'lucide-react';
import * as XLSX from 'xlsx';

interface ExportButtonProps {
  data: any[];
  filename: string;
  format?: 'csv' | 'excel' | 'json';
  onExport?: () => void;
}

export const ExportButton = ({ 
  data, 
  filename, 
  format = 'excel',
  onExport 
}: ExportButtonProps) => {
  const handleExport = () => {
    if (format === 'excel') {
      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Data');
      XLSX.writeFile(wb, `${filename}.xlsx`);
    } else if (format === 'csv') {
      const ws = XLSX.utils.json_to_sheet(data);
      const csv = XLSX.utils.sheet_to_csv(ws);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${filename}.csv`;
      link.click();
    } else {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${filename}.json`;
      link.click();
    }
    onExport?.();
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleExport}
      className="bg-[var(--color-surface-container)] border-[var(--color-outline-variant)] hover:border-[var(--color-primary)]/30"
    >
      <Download className="w-4 h-4 mr-2" />
      Export
    </Button>
  );
};
