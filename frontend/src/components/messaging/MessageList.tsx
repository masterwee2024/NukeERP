import { useRef, useEffect } from "react";
import type { Message } from "@/hooks/useMessaging";

interface MessageListProps {
  messages: Message[];
  typingUsers: string[];
}

function formatTime(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function formatDateLabel(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric", year: "numeric" });
}

export default function MessageList({ messages, typingUsers }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  let lastDate = "";

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-1">
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-sm text-secondary-400">
          No messages yet. Start the conversation!
        </div>
      )}

      {messages.map((msg) => {
        if (msg.is_deleted) return null;

        const dateKey = msg.created_at ? new Date(msg.created_at).toDateString() : "";
        const showDate = dateKey && dateKey !== lastDate;
        if (dateKey) lastDate = dateKey;

        return (
          <div key={msg.id}>
            {showDate && (
              <div className="flex items-center gap-3 py-3">
                <div className="flex-1 border-t border-secondary-200" />
                <span className="text-[10px] font-medium text-secondary-400 uppercase">{formatDateLabel(msg.created_at)}</span>
                <div className="flex-1 border-t border-secondary-200" />
              </div>
            )}

            <div className={`group flex items-start gap-3 px-2 py-1.5 rounded-md hover:bg-secondary-50 ${
              msg.content_type === "system" ? "opacity-70" : ""
            }`}>
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary-700">
                {msg.sender_email?.charAt(0).toUpperCase() || "?"}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-semibold text-secondary-800">
                    {msg.sender_email?.split("@")[0] || "System"}
                  </span>
                  <span className="text-[10px] text-secondary-400">{formatTime(msg.created_at)}</span>
                  {msg.is_edited && <span className="text-[10px] text-secondary-400">(edited)</span>}
                </div>
                <p className="mt-0.5 text-sm text-secondary-700 whitespace-pre-wrap break-words">
                  {msg.content}
                </p>
              </div>
            </div>
          </div>
        );
      })}

      {typingUsers.length > 0 && (
        <div className="px-2 py-1 text-xs text-secondary-400 italic">
          {typingUsers.join(", ")} typing{typingUsers.length > 1 ? "" : "s"}...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
