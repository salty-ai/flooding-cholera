/* eslint-disable react-refresh/only-export-components */
import { useState, useRef, useEffect } from 'react';
import { toPng, toSvg } from 'html-to-image';
import { showToast } from '../common/Toast';

interface ExportButtonProps {
  targetRef: React.RefObject<HTMLElement>;
  filename?: string;
  className?: string;
}

type ExportFormat = 'png' | 'svg';

export default function ExportButton({
  targetRef,
  filename = 'chart',
  className = '',
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExport = async (format: ExportFormat) => {
    if (!targetRef.current) {
      showToast.error('Unable to export: chart element not found');
      return;
    }

    setIsExporting(true);
    setIsOpen(false);

    try {
      let dataUrl: string;
      const options = {
        backgroundColor: '#ffffff',
        quality: 1,
        pixelRatio: 2,
      };

      if (format === 'svg') {
        dataUrl = await toSvg(targetRef.current, options);
      } else {
        dataUrl = await toPng(targetRef.current, options);
      }

      // Create download link
      const link = document.createElement('a');
      link.download = `${filename}.${format}`;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      showToast.success(`Chart exported as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export failed:', error);
      showToast.error('Failed to export chart. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div ref={menuRef} className={`relative inline-block ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
        aria-label="Export chart"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        {isExporting ? (
          <svg
            className="w-4 h-4 animate-spin"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
        )}
        <span>Export</span>
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full mt-1 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-50 min-w-[100px]"
          role="menu"
          aria-label="Export options"
        >
          <button
            onClick={() => handleExport('png')}
            className="w-full px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            role="menuitem"
          >
            Export as PNG
          </button>
          <button
            onClick={() => handleExport('svg')}
            className="w-full px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            role="menuitem"
          >
            Export as SVG
          </button>
        </div>
      )}
    </div>
  );
}

// CSV Export utility function
export function exportToCSV(data: Record<string, unknown>[], filename: string) {
  if (data.length === 0) {
    showToast.error('No data to export');
    return;
  }

  const headers = Object.keys(data[0]);
  const csvRows = [
    headers.join(','),
    ...data.map((row) =>
      headers
        .map((header) => {
          const value = row[header];
          // Handle strings with commas or quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value ?? '';
        })
        .join(',')
    ),
  ];

  const csvContent = csvRows.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  showToast.success('Data exported as CSV');
}
