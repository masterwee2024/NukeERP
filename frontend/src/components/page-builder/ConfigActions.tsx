import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useBuilderStore } from "./builderStore";

interface ConfigActionsProps {
  onSave: () => Promise<void>;
  onPublish: () => Promise<void>;
  onExport: () => void;
  onImport: (data: string) => void;
  onClone: () => void;
}

export default function ConfigActions({
  onSave,
  onPublish,
  onExport,
  onImport,
  onClone,
}: ConfigActionsProps) {
  const navigate = useNavigate();
  const { confirm } = useConfirm();
  const isDirty = useBuilderStore((s) => s.isDirty);
  const previewMode = useBuilderStore((s) => s.previewMode);
  const setPreviewMode = useBuilderStore((s) => s.setPreviewMode);
  const config = useBuilderStore((s) => s.config);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const importRef = useRef<HTMLTextAreaElement>(null);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await onSave();
    } finally {
      setSaving(false);
    }
  }, [onSave]);

  const handlePublish = useCallback(async () => {
    const ok = await confirm({
      title: "Publish Page Config",
      message:
        "Publishing will make this configuration active for all users. Continue?",
      variant: "warning",
      confirmText: "Publish",
    });
    if (!ok) return;
    setPublishing(true);
    try {
      await onPublish();
    } finally {
      setPublishing(false);
    }
  }, [onPublish, confirm]);

  const handleExport = useCallback(() => {
    onExport();
  }, [onExport]);

  const handleImportConfirm = useCallback(async () => {
    try {
      JSON.parse(importText);
      onImport(importText);
      setShowImport(false);
      setImportText("");
    } catch {
      await confirm({
        title: "Invalid JSON",
        message: "The imported data is not valid JSON. Please check and try again.",
        variant: "danger",
        confirmText: "OK",
      });
    }
  }, [importText, onImport, confirm]);

  const handleClone = useCallback(async () => {
    const ok = await confirm({
      title: "Clone Page Config",
      message: `Clone "${config.page_title || "Untitled"}" to a new configuration?`,
      variant: "info",
      confirmText: "Clone",
    });
    if (!ok) return;
    onClone();
  }, [config.page_title, onClone, confirm]);

  const handleDiscard = useCallback(async () => {
    const ok = await confirm({
      title: "Discard Changes",
      message: "You have unsaved changes. Are you sure you want to discard them?",
      variant: "danger",
      confirmText: "Discard",
    });
    if (!ok) return;
    navigate("/app/admin/page-builder");
  }, [confirm, navigate]);

  return (
    <div className="flex items-center gap-2 border-b border-secondary-200 bg-white px-4 py-2">
      {/* Preview toggle */}
      <button
        onClick={() =>
          setPreviewMode(previewMode === "desktop" ? "mobile" : "desktop")
        }
        className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
          previewMode === "mobile"
            ? "bg-primary-100 text-primary-700"
            : "bg-secondary-100 text-secondary-600 hover:bg-secondary-200"
        }`}
        title={previewMode === "desktop" ? "Switch to mobile preview" : "Switch to desktop preview"}
      >
        {previewMode === "desktop" ? (
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        )}
        {previewMode === "desktop" ? "Desktop" : "Mobile"}
      </button>

      <div className="h-4 w-px bg-secondary-200" />

      {/* Save */}
      <button
        onClick={handleSave}
        disabled={saving || !isDirty}
        className="rounded-md bg-primary-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save"}
      </button>

      {/* Publish */}
      <button
        onClick={handlePublish}
        disabled={publishing}
        className="rounded-md bg-success-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-success-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {publishing ? "Publishing..." : "Publish"}
      </button>

      <div className="h-4 w-px bg-secondary-200" />

      {/* Export */}
      <button
        onClick={handleExport}
        className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
      >
        Export JSON
      </button>

      {/* Import */}
      <button
        onClick={() => setShowImport(true)}
        className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
      >
        Import JSON
      </button>

      {/* Clone */}
      <button
        onClick={handleClone}
        className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
      >
        Clone
      </button>

      <div className="flex-1" />

      {/* Discard / Back */}
      {isDirty && (
        <button
          onClick={handleDiscard}
          className="rounded-md border border-danger-200 px-3 py-1.5 text-xs font-medium text-danger-600 hover:bg-danger-50"
        >
          Discard
        </button>
      )}

      {!isDirty && (
        <button
          onClick={() => navigate("/app/admin/page-builder")}
          className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
        >
          Back
        </button>
      )}

      {/* Import dialog */}
      {showImport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowImport(false)} />
          <div className="relative w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <h3 className="mb-2 text-lg font-semibold text-secondary-900">Import JSON</h3>
            <p className="mb-3 text-sm text-secondary-500">
              Paste the JSON configuration below to import.
            </p>
            <textarea
              ref={importRef}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              rows={10}
              className="w-full rounded-md border border-secondary-300 p-3 font-mono text-xs focus:border-primary-500 focus:outline-none"
              placeholder='{"page_title": "...", "fields": [...]}'
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowImport(false);
                  setImportText("");
                }}
                className="rounded-md border border-secondary-300 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImportConfirm}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700"
              >
                Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
