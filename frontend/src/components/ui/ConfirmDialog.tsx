import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  type ReactNode,
} from "react";

interface ConfirmConfig {
  title: string;
  message: string;
  variant?: "danger" | "warning" | "info";
  confirmText?: string;
  cancelText?: string;
}

interface ConfirmContextValue {
  confirm: (config: ConfirmConfig) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

export function useConfirm(): ConfirmContextValue {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error("useConfirm must be used within a ConfirmProvider");
  }
  return context;
}


// ── useAction — standard Confirm → Execute → Result pattern ──

export interface ActionConfig<TReturn = void> {
  /** Confirm step — omit to skip confirmation */
  confirm?: ConfirmConfig;
  /** The actual action (API call, etc.) */
  action: () => Promise<TReturn> | TReturn;
  /** Success dialog — omit to skip */
  success?: { title: string; message?: string; variant?: "info" | "warning" | "danger" };
  /** Error dialog title (default "Error") */
  errorTitle?: string;
  /** Called after success dialog closes, receives action return value */
  onSuccess?: (result: TReturn) => void | Promise<void>;
}

export function useAction() {
  const { confirm } = useConfirm();

  async function execute<TReturn = void>(
    cfg: ActionConfig<TReturn>,
  ): Promise<TReturn | undefined> {
    // 1. Confirm
    if (cfg.confirm) {
      const ok = await confirm(cfg.confirm);
      if (!ok) return undefined;
    }

    try {
      // 2. Execute
      const result = await cfg.action();

      // 3. Success dialog
      if (cfg.success) {
        await confirm({
          title: cfg.success.title,
          message: cfg.success.message ?? "",
          variant: cfg.success.variant ?? "info",
          confirmText: "OK",
        });
      }

      if (cfg.onSuccess) {
        await cfg.onSuccess(result);
      }

      return result as TReturn;
    } catch (err: unknown) {
      // 4. Error dialog
      await confirm({
        title: cfg.errorTitle ?? "Error",
        message: err instanceof Error ? err.message : "Please contact system administrator.",
        variant: "danger",
        confirmText: "OK",
      });
      return undefined;
    }
  }

  return { execute };
}

interface ConfirmState {
  open: boolean;
  config: ConfirmConfig;
  resolve: ((value: boolean) => void) | null;
}

const variantStyles = {
  danger: {
    icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z",
    iconColor: "text-danger-500",
    buttonBg: "bg-danger-600 hover:bg-danger-700",
  },
  warning: {
    icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z",
    iconColor: "text-warning-500",
    buttonBg: "bg-warning-600 hover:bg-warning-700",
  },
  info: {
    icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    iconColor: "text-primary-500",
    buttonBg: "bg-primary-600 hover:bg-primary-700",
  },
};

function ConfirmModal({
  config,
  loading,
  onConfirm,
  onCancel,
}: {
  config: ConfirmConfig;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const variant = config.variant || "info";
  const styles = variantStyles[variant];
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    const dialog = dialogRef.current;
    if (dialog) {
      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      focusable[0]?.focus();
    }
    return () => {
      previousFocusRef.current?.focus();
    };
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape" && !loading) {
      onCancel();
    }
    if (e.key === "Enter" && !loading) {
      onConfirm();
    }
    if (e.key === "Tab") {
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onKeyDown={handleKeyDown}
        className="relative w-full max-w-sm rounded-lg bg-white p-6 shadow-xl"
      >
        <div className="flex items-start gap-4">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary-100 ${styles.iconColor}`}
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={styles.icon}
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 id="confirm-title" className="text-lg font-semibold text-secondary-900">
              {config.title}
            </h3>
            <p className="mt-2 text-sm text-secondary-600">{config.message}</p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded-md border border-secondary-300 bg-white px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
          >
            {config.cancelText || "Cancel"}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${styles.buttonBg}`}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Processing...
              </span>
            ) : (
              config.confirmText || "Confirm"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ConfirmState>({
    open: false,
    config: { title: "", message: "" },
    resolve: null,
  });
  const [loading, setLoading] = useState(false);

  const confirm = useCallback((config: ConfirmConfig): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ open: true, config, resolve });
    });
  }, []);

  const handleConfirm = useCallback(async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 100));
    setState((prev) => {
      prev.resolve?.(true);
      return { ...prev, open: false, resolve: null };
    });
    setLoading(false);
  }, []);

  const handleCancel = useCallback(() => {
    setState((prev) => {
      prev.resolve?.(false);
      return { ...prev, open: false, resolve: null };
    });
  }, []);

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {state.open && (
        <ConfirmModal
          config={state.config}
          loading={loading}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}
    </ConfirmContext.Provider>
  );
}
