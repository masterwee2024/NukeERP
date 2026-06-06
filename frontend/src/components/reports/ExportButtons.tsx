import { useState } from "react";
import api from "@/lib/api";

interface ExportButtonsProps {
  reportCode: string;
  filters: Record<string, unknown>;
}

export default function ExportButtons({ reportCode, filters }: ExportButtonsProps) {
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setExporting(format);
    try {
      const resp = await api.post(`/financial/reports/${reportCode}/export/`, {
        format,
        params: filters,
      });
      const { export_id } = resp.data;

      // Poll for completion
      const poll = setInterval(async () => {
        const statusResp = await api.get(`/financial/exports/${export_id}/`);
        const { status, download_url } = statusResp.data;
        if (status === "ready") {
          clearInterval(poll);
          if (download_url) {
            window.open(download_url, "_blank");
          }
          setExporting(null);
        } else if (status === "failed") {
          clearInterval(poll);
          setExporting(null);
          alert("Export failed. Please try again.");
        }
      }, 1000);

      // timeout after 30 seconds
      setTimeout(() => {
        clearInterval(poll);
        setExporting(null);
      }, 30000);
    } catch {
      setExporting(null);
      alert("Export request failed.");
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => handleExport("csv")}
        disabled={exporting !== null}
        className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        {exporting === "csv" ? "Exporting..." : "Export CSV"}
      </button>
      <button
        onClick={() => handleExport("pdf")}
        disabled={exporting !== null}
        className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        {exporting === "pdf" ? "Exporting..." : "Export PDF"}
      </button>
      <button
        onClick={() => handleExport("xlsx")}
        disabled={exporting !== null}
        className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        {exporting === "xlsx" ? "Exporting..." : "Export Excel"}
      </button>
    </div>
  );
}
