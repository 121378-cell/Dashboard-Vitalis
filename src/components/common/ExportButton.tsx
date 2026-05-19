import React from 'react';
import { Button } from '../ui/button';
import { Download, Share2 } from 'lucide-react';
import * as ExcelJS from 'exceljs';

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
      const workbook = new ExcelJS.Workbook();
      const worksheet = workbook.addWorksheet('Data');
      
      // Add headers
      if (data.length > 0) {
        const headers = Object.keys(data[0]);
        worksheet.addRow(headers);
        
        // Add data rows
        data.forEach(row => {
          const values = headers.map(header => row[header]);
          worksheet.addRow(values);
        });
      }
      
      workbook.xlsx.writeBuffer().then((buffer) => {
        const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${filename}.xlsx`;
        link.click();
      });
    } else if (format === 'csv') {
      // Convert to CSV manually since we removed xlsx
      if (data.length === 0) {
        const blob = new Blob([''], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${filename}.csv`;
        link.click();
        return;
      }
      
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(','),
        ...data.map(row => 
          headers.map(header => {
            const value = row[header];
            // Escape quotes and wrap in quotes if necessary
            const escaped = ('' + value).replace(/"/g, '""');
            if (value.includes(',') || value.includes('\n') || value.includes('"')) {
              return `"${escaped}"`;
            }
            return escaped;
          }).join(',')
        )
      ].join('\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
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
