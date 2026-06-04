import type { Message } from "@/hooks/useMessaging";

interface ThreadPanelProps {
  parentMessage: Message;
  replies: Message[];
  onSendReply: (content: string) => void;
  onClose: () => void;
}

export default function ThreadPanel({ parentMessage, replies, onSendReply, onClose }: ThreadPanelProps) {
  return (
    <div className="flex h-full flex-col border-l border-secondary-200 bg-white">
      <div className="flex items-center justify-between border-b border-secondary-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-secondary-800">Thread</h3>
        <button onClick={onClose} className="text-secondary-400 hover:text-secondary-600">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="rounded-lg bg-secondary-50 p-3">
          <p className="text-xs font-semibold text-secondary-700">{parentMessage.sender_email?.split("@")[0] || "Unknown"}</p>
          <p className="mt-1 text-sm text-secondary-600">{parentMessage.content}</p>
        </div>

        <div className="border-t border-secondary-100 pt-3 space-y-3">
          {replies.length === 0 && (
            <p className="text-xs text-secondary-400 text-center">No replies yet</p>
          )}
          {replies.map((reply) => (
            <div key={reply.id} className="flex items-start gap-2">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary-200 text-[10px] font-semibold text-secondary-600">
                {reply.sender_email?.charAt(0).toUpperCase() || "?"}
              </div>
              <div>
                <p className="text-xs font-semibold text-secondary-700">{reply.sender_email?.split("@")[0]}</p>
                <p className="text-sm text-secondary-600">{reply.content}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-secondary-200 p-3">
        <textarea
          placeholder="Reply in thread..."
          rows={2}
          className="w-full resize-none rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              const target = e.currentTarget;
              const val = target.value.trim();
              if (val) {
                onSendReply(val);
                target.value = "";
              }
            }
          }}
        />
      </div>
    </div>
  );
}
