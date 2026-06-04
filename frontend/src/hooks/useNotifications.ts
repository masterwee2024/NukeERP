import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface NotificationType {
  name: string;
  slug: string;
}

export interface Notification {
  id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export function useNotifications() {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Fetch paginated notifications
  const { data: notificationData = { results: [], count: 0 }, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => {
      const { data } = await api.get("/core/notifications/");
      return data as { results: Notification[]; count: number };
    },
    staleTime: 30000,
  });

  // Fetch unread count
  const { data: unreadData = { count: 0 } } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get("/core/notifications/unread-count/");
      return data as { count: number };
    },
    staleTime: 30000,
  });

  // Fetch push subscription status
  const { data: pushStatus = { subscribed: false } } = useQuery({
    queryKey: ["notifications", "push-status"],
    queryFn: async () => {
      const { data } = await api.get("/core/notifications/push/status/");
      return data as { subscribed: boolean };
    },
    staleTime: 60000,
  });

  // Mark single as read
  const markReadMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.put(`/core/notifications/${id}/read/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  // Mark all as read
  const markAllReadMutation = useMutation({
    mutationFn: async () => {
      await api.put("/core/notifications/read-all/");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  // Push subscribe
  const subscribePushMutation = useMutation({
    mutationFn: async (sub: {
      endpoint: string;
      p256dh: string;
      auth: string;
      user_agent?: string;
    }) => {
      await api.post("/core/notifications/push/subscribe/", sub);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", "push-status"] });
    },
  });

  // Push unsubscribe
  const unsubscribePushMutation = useMutation({
    mutationFn: async () => {
      await api.delete("/core/notifications/push/unsubscribe/");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", "push-status"] });
    },
  });

  // Handle WebSocket connection
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/notifications/?token=${encodeURIComponent(
        token || ""
      )}`;

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "notification_message") {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
            queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
          } else if (data.type === "unread_count_update") {
            queryClient.setQueryData(["notifications", "unread-count"], {
              count: data.unread_count,
            });
          }
        } catch (err) {
          console.error("Error parsing WS message", err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(() => {
          connect();
        }, 5000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        ws.close();
      };
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

  const subscribeToPushNotifications = async () => {
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        throw new Error("Notification permission not granted");
      }

      if (!("serviceWorker" in navigator)) {
        throw new Error("Service Worker not supported in this browser");
      }

      const registration = await navigator.serviceWorker.ready;
      if (!registration) {
        throw new Error("No active Service Worker registration found");
      }

      // Fetch VAPID key from backend
      const { data: keyData } = await api.get("/core/notifications/push/vapid-key/");
      const vapidPublicKey = keyData.public_key;

      if (!vapidPublicKey) {
        throw new Error("VAPID key not configured on server");
      }

      const convertedVapidKey = urlBase64ToUint8Array(vapidPublicKey);

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedVapidKey,
      });

      const rawSub = subscription.toJSON();
      if (!rawSub.endpoint || !rawSub.keys?.p256dh || !rawSub.keys?.auth) {
        throw new Error("Subscription missing credentials");
      }

      await subscribePushMutation.mutateAsync({
        endpoint: rawSub.endpoint,
        p256dh: rawSub.keys.p256dh,
        auth: rawSub.keys.auth,
        user_agent: navigator.userAgent,
      });
    } catch (err) {
      console.error("Failed to subscribe to Web Push:", err);
      throw err;
    }
  };

  const unsubscribeFromPushNotifications = async () => {
    try {
      if ("serviceWorker" in navigator) {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
          await subscription.unsubscribe();
        }
      }
      await unsubscribePushMutation.mutateAsync();
    } catch (err) {
      console.error("Failed to unsubscribe from Web Push:", err);
      throw err;
    }
  };

  return {
    notifications: notificationData.results || [],
    totalCount: notificationData.count || 0,
    unreadCount: unreadData.count || 0,
    isLoading,
    isWsConnected: wsConnected,
    isPushSubscribed: pushStatus.subscribed,
    markAsRead: (id: string) => markReadMutation.mutateAsync(id),
    markAllAsRead: () => markAllReadMutation.mutateAsync(),
    subscribePush: subscribeToPushNotifications,
    unsubscribePush: unsubscribeFromPushNotifications,
  };
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
