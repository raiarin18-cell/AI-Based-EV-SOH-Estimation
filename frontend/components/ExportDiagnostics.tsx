import React, { useState } from "react";
import { Download, FileText, CheckCircle2 } from "lucide-react";
import { fetchDiagnosticsSummary, getDiagnosticReportHtmlUrl } from "../services/api";

export const ExportDiagnostics: React.FC = () => {
  const [downloading, setDownloading] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);

  const handleExportJSON = async () => {
    setDownloading(true);
    try {
      const data = await fetchDiagnosticsSummary();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `battery_diagnostics_${data.report_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex items-center space-x-3">
      <button
        onClick={handleExportJSON}
        disabled={downloading}
        className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-200 px-3.5 py-2 rounded-lg text-xs font-medium transition border border-gray-700 disabled:opacity-50"
      >
        {success ? (
          <>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Downloaded
          </>
        ) : (
          <>
            <Download className="w-4 h-4" /> {downloading ? "Exporting..." : "Export JSON"}
          </>
        )}
      </button>

      <a
        href={getDiagnosticReportHtmlUrl()}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/25 transition"
      >
        <FileText className="w-4 h-4" /> View Certificate
      </a>
    </div>
  );
};
