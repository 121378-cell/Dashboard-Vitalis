import React, { useRef } from 'react';
import { Button } from '../ui/button';
import { Share2 } from 'lucide-react';

interface ChartExportButtonProps {
  chartRef: React.RefObject<HTMLDivElement>;
  filename?: string;
}

export const ChartExportButton = ({ chartRef, filename = 'chart' }: ChartExportButtonProps) => {
  const handleExport = async () => {
    const element = chartRef.current;
    if (!element) return;

    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(element, {
        backgroundColor: 'var(--color-background)',
        scale: 2,
        useCORS: true,
        allowTaint: true,
      });
      
      const link = document.createElement('a');
      link.download = `${filename}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleExport}
      className="bg-[var(--color-surface-container)] border-[var(--color-outline-variant)] hover:border-[var(--color-primary)]/30"
    >
      <Share2 className="w-4 h-4 mr-2" />
      Export Chart
    </Button>
  );
};
