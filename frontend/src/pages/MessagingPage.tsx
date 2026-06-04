import { useState } from "react";
import { useMessaging } from "@/hooks/useMessaging";
import ChannelList from "@/components/messaging/ChannelList";
import MessageList from "@/components/messaging/MessageList";
import MessageInput from "@/components/messaging/MessageInput";

export default function MessagingPage() {
  const {
    channels,
    messages,
    activeChannelId,
    setActiveChannelId,
    wsConnected,
    typingUsers,
    sendMessage,
    sendTyping,
  } = useMessaging();

  const [showChannels, setShowChannels] = useState(false);

  const activeChannel = channels.find((c) => c.id === activeChannelId);
  const channelTyping = activeChannelId ? typingUsers[activeChannelId] || [] : [];

  const handleSend = (content: string) => {
    if (activeChannelId) {
      sendMessage(activeChannelId, content);
    }
  };

  const handleTyping = () => {
    if (activeChannelId) {
      sendTyping(activeChannelId);
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Channel sidebar — desktop persistent, mobile drawer */}
      <div className={`${
        showChannels ? "fixed inset-0 z-40 flex" : "hidden"
      } lg:relative lg:flex lg:w-60 lg:shrink-0`}>
        {showChannels && (
          <div className="fixed inset-0 bg-black/30 lg:hidden" onClick={() => setShowChannels(false)} />
        )}
        <div className={`relative w-72 border-r border-secondary-200 bg-white lg:w-full ${
          showChannels ? "z-50" : "hidden lg:block"
        }`}>
          <ChannelList
            channels={channels}
            activeId={activeChannelId}
            onSelect={setActiveChannelId}
            onClose={() => setShowChannels(false)}
          />
        </div>
      </div>

      {/* Main message area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-secondary-200 bg-white px-4 py-3">
          <button
            onClick={() => setShowChannels(true)}
            className="lg:hidden text-secondary-500 hover:text-secondary-700"
            aria-label="Toggle channel list"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {activeChannel ? (
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-secondary-800">
                # {activeChannel.name}
              </span>
              <span
                className={`h-2 w-2 rounded-full ${wsConnected ? "bg-green-500" : "bg-yellow-500"}`}
                title={wsConnected ? "Connected" : "Reconnecting..."}
              />
            </div>
          ) : (
            <span className="text-sm text-secondary-400">Select a channel</span>
          )}
        </div>

        {activeChannelId ? (
          <>
            <MessageList messages={messages} typingUsers={channelTyping} />
            <MessageInput onSend={handleSend} onTyping={handleTyping} />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-secondary-400">
            Select a channel to start messaging
          </div>
        )}
      </div>
    </div>
  );
}
