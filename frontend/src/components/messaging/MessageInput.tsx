import { useState, useRef, useCallback } from "react";

interface MessageInputProps {
  onSend: (content: string) => void;
  onTyping: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function MessageInput({ onSend, onTyping, disabled, placeholder }: MessageInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    onTyping();

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  };

  return (
    <div className="border-t border-secondary-200 bg-white p-3">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Type a message... (Enter to send, Shift+Enter for newline)"}
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none disabled:bg-secondary-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="shrink-0 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
