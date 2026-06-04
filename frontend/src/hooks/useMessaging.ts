import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface Channel {
  id: string;
  name: string;
  description: string;
  type: string;
  is_archived: boolean;
  company_id: string;
  created_by_id: string | null;
  created_at: string | null;
}

export interface Message {
  id: string;
  channel_id: string;
  sender_id: string | null;
  sender_email: string;
  content: string;
  content_type: string;
  reply_to_id: string | null;
  is_edited: boolean;
  is_deleted: boolean;
  created_at: string | null;
}

export function useMessaging() {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);
  const [typingUsers, setTypingUsers] = useState<Record<string, string[]>>({});

  const { data: channelsData = { count: 0, results: [] as Channel[] } } = useQuery({
    queryKey: ["channels"],
    queryFn: async () => {
      const { data } = await api.get("/core/messaging/channels/");
      return data as { count: number; results: Channel[] };
    },
    staleTime: 30000,
  });

  const { data: messagesData = { count: 0, results: [] as Message[] } } = useQuery({
    queryKey: ["messages", activeChannelId],
    queryFn: async () => {
      if (!activeChannelId) return { count: 0, results: [] };
      const { data } = await api.get(`/core/messaging/channels/${activeChannelId}/messages/`);
      return data as { count: number; results: Message[] };
    },
    enabled: !!activeChannelId,
    staleTime: 5000,
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (params: { channel_id: string; content: string; reply_to_id?: string }) => {
      const { data } = await api.post(`/core/messaging/channels/${params.channel_id}/messages/`, {
        content: params.content,
        reply_to_id: params.reply_to_id || null,
      });
      return data as Message;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages", activeChannelId] });
    },
  });

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/?token=${encodeURIComponent(token || "")}`;

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => setWsConnected(true);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "chat_message") {
            queryClient.invalidateQueries({ queryKey: ["messages"] });
          } else if (data.type === "typing") {
            setTypingUsers((prev) => ({
              ...prev,
              [data.channel_id]: [...(prev[data.channel_id] || []).filter((u) => u !== data.user_email), data.user_email],
            }));
            setTimeout(() => {
              setTypingUsers((prev) => ({
                ...prev,
                [data.channel_id]: (prev[data.channel_id] || []).filter((u) => u !== data.user_email),
              }));
            }, 3000);
          }
        } catch (err) {
          console.error("WS parse error", err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, [queryClient]);

  const sendTyping = (channelId: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "typing", channel_id: channelId }));
    }
  };

  const sendMessage = async (channelId: string, content: string, replyToId?: string) => {
    await sendMessageMutation.mutateAsync({ channel_id: channelId, content, reply_to_id: replyToId });
  };

  return {
    channels: channelsData.results,
    messages: messagesData.results,
    activeChannelId,
    setActiveChannelId,
    wsConnected,
    typingUsers,
    sendMessage,
    sendTyping,
    isSending: sendMessageMutation.isPending,
  };
}
