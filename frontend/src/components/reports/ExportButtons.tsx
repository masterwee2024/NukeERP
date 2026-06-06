import { useState, useRef } from "react";
import api from "@/lib/api";

async function downloadWithAuth(url: string, filename: string) {
  const resp = await api.get(url, { responseType: "blob" });
  const blob = new Blob([resp.data]);
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}

interface ExportButtonsProps {
  reportCode: string;
  filters: Record<string, unknown>;
}

export default function ExportButtons({ reportCode, filters }: ExportButtonsProps) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const handleExport = async (format: string) => {
    setExportError(null);
    setExporting(format);
    try {
      const resp = await api.post(`/financial/reports/${reportCode}/export/`, {
        format,
        params: filters,
      });
      const { export_id } = resp.data;

      // Poll for completion
      pollingRef.current = setInterval(async () => {
        try {
          const statusResp = await api.get(`/financial/exports/${export_id}/`);
          const { status, download_url } = statusResp.data;
          if (status === "ready") {
            stopPolling();
            if (download_url) {
              await downloadWithAuth(download_url, `${reportCode}.${format}`);
            }
            setExporting(null);
          } else if (status === "failed") {
            stopPolling();
            setExporting(null);
            setExportError("Export failed. Please try again.");
          }
        } catch {
          stopPolling();
          setExporting(null);
          setExportError("Export failed. Please try again.");
        }
      }, 1000);

      // timeout after 30 seconds
      setTimeout(() => {
        if (pollingRef.current) {
          stopPolling();
          setExporting(null);
          setExportError("Export timed out. Please try again.");
        }
      }, 30000);
    } catch {
      setExporting(null);
      setExportError("Export request failed. Please try again.");
    }
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleExport("csv")}
          disabled={exporting !== null}
          className="rounded-md border border-secondary-300 bg-white px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
        >
          {exporting === "csv" ? "Exporting..." : "Export CSV"}
        </button>
        <button
          onClick={() => handleExport("pdf")}
          disabled={exporting !== null}
          className="rounded-md border border-secondary-300 bg-white px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
        >
          {exporting === "pdf" ? "Exporting..." : "Export PDF"}
        </button>
        <button
          onClick={() => handleExport("xlsx")}
          disabled={exporting !== null}
          className="rounded-md border border-secondary-300 bg-white px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
        >
          {exporting === "xlsx" ? "Exporting..." : "Export Excel"}
        </button>
      </div>
      {exportError && (
        <p className="mt-1 text-xs text-danger-600">{exportError}</p>
      )}
    </div>
  );
}
