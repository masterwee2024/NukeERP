import { useState, useCallback } from "react";

interface JSONEditorProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export default function JSONEditor({ value, onChange, label }: JSONEditorProps) {
  const [text, setText] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);

  const handleChange = useCallback(
    (newText: string) => {
      setText(newText);
      try {
        JSON.parse(newText);
        setError(null);
        onChange(newText);
      } catch (e) {
        setError(e instanceof SyntaxError ? e.message : "Invalid JSON");
      }
    },
    [onChange]
  );

  const handleBlur = useCallback(() => {
    setFocused(false);
    try {
      const parsed = JSON.parse(text);
      setText(JSON.stringify(parsed, null, 2));
      setError(null);
      onChange(JSON.stringify(parsed, null, 2));
    } catch {
      // keep as-is
    }
  }, [text, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = e.currentTarget.selectionStart;
        const end = e.currentTarget.selectionEnd;
        const newText = text.substring(0, start) + "  " + text.substring(end);
        setText(newText);
        onChange(newText);
        setTimeout(() => {
          e.currentTarget.selectionStart = e.currentTarget.selectionEnd = start + 2;
        }, 0);
      }
    },
    [text, onChange]
  );

  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-xs font-medium text-secondary-600">{label}</label>
      )}
      <textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        rows={6}
        spellCheck={false}
        className={`w-full rounded-md border px-2.5 py-2 font-mono text-xs leading-relaxed focus:outline-none ${
          error
            ? "border-danger-300 ring-1 ring-danger-200"
            : focused
              ? "border-primary-400 ring-1 ring-primary-200"
              : "border-secondary-300"
        }`}
        placeholder="{ ... }"
      />
      {error && (
        <p className="text-[10px] text-danger-500">{error}</p>
      )}
    </div>
  );
}
