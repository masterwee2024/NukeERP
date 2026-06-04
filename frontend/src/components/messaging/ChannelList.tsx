import { useState } from "react";
import type { Channel } from "@/hooks/useMessaging";

interface ChannelListProps {
  channels: Channel[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onClose?: () => void;
}

export default function ChannelList({ channels, activeId, onSelect, onClose }: ChannelListProps) {
  const [search, setSearch] = useState("");

  const filtered = search
    ? channels.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : channels;

  const publicChannels = filtered.filter((c) => c.type === "public" || c.type === "private");
  const dmChannels = filtered.filter((c) => c.type === "direct");
  const systemChannels = filtered.filter((c) => c.type === "system");

  const ChannelItem = ({ channel }: { channel: Channel }) => {
    const badge = channel.type === "direct" ? "DM" : channel.type === "system" ? "💬" : "#";
    return (
      <button
        onClick={() => {
          onSelect(channel.id);
          onClose?.();
        }}
        className={`w-full flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
          activeId === channel.id
            ? "bg-primary-100 text-primary-700 font-medium"
            : "text-secondary-600 hover:bg-secondary-100 hover:text-secondary-800"
        }`}
      >
        <span className="w-5 text-center text-xs font-mono text-secondary-400">{badge}</span>
        <span className="truncate">{channel.name}</span>
      </button>
    );
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-secondary-200 p-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-secondary-800">Channels</h2>
          {onClose && (
            <button onClick={onClose} className="text-secondary-400 hover:text-secondary-600 lg:hidden">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search channels..."
          className="w-full rounded-md border border-secondary-300 px-3 py-1.5 text-xs focus:border-primary-500 focus:outline-none"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {publicChannels.length > 0 && (
          <div>
            <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-secondary-400">Channels</p>
            {publicChannels.map((ch) => (
              <ChannelItem key={ch.id} channel={ch} />
            ))}
          </div>
        )}

        {dmChannels.length > 0 && (
          <div>
            <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-secondary-400">Direct Messages</p>
            {dmChannels.map((ch) => (
              <ChannelItem key={ch.id} channel={ch} />
            ))}
          </div>
        )}

        {systemChannels.length > 0 && (
          <div>
            <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-secondary-400">System</p>
            {systemChannels.map((ch) => (
              <ChannelItem key={ch.id} channel={ch} />
            ))}
          </div>
        )}

        {filtered.length === 0 && (
          <p className="px-3 text-xs text-secondary-400">No channels found</p>
        )}
      </div>
    </div>
  );
}
