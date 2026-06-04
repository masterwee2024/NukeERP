import { useState, useEffect } from "react";
import api from "@/lib/api";

export default function PushNotificationSetup() {
  const [supported, setSupported] = useState(false);
  const [subscribed, setSubscribed] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if ("Notification" in window && "serviceWorker" in navigator && "PushManager" in window) {
      setSupported(true);
      setPermission(Notification.permission);
    }
  }, []);

  useEffect(() => {
    if (supported && permission === "granted") {
      api.get("/core/notifications/push/status/").then(({ data }) => {
        setSubscribed(data.subscribed);
      }).catch(() => {});
    }
  }, [supported, permission]);

  const urlBase64ToUint8Array = (base64: string) => {
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = window.atob(b64);
    return Uint8Array.from(raw.split("").map((c) => c.charCodeAt(0)));
  };

  const handleSubscribe = async () => {
    if (!supported) return;
    setLoading(true);

    try {
      const perm = await Notification.requestPermission();
      setPermission(perm);
      if (perm !== "granted") {
        setLoading(false);
        return;
      }

      const registration = await navigator.serviceWorker.ready;

      const { data: vapidData } = await api.get("/core/notifications/push/vapid-key/");
      const publicKey = vapidData.public_key;
      if (!publicKey) {
        throw new Error("VAPID public key not configured");
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      await api.post("/core/notifications/push/subscribe/", {
        endpoint: subscription.endpoint,
        p256dh: btoa(
          String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh")!))
        ),
        auth: btoa(
          String.fromCharCode(...new Uint8Array(subscription.getKey("auth")!))
        ),
        user_agent: navigator.userAgent,
      });

      setSubscribed(true);
    } catch (err) {
      console.error("Push subscription failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUnsubscribe = async () => {
    setLoading(true);
    try {
      await api.delete("/core/notifications/push/unsubscribe/");
      setSubscribed(false);
    } catch (err) {
      console.error("Push unsubscription failed:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!supported) {
    return (
      <div className="rounded-lg border border-secondary-200 bg-secondary-50 p-4 text-sm text-secondary-500">
        Push notifications are not supported on this browser.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-secondary-700">
            Push Notifications
          </h3>
          <p className="text-xs text-secondary-500">
            {subscribed
              ? "You will receive push notifications for new approvals."
              : "Enable push notifications to get real-time alerts."}
          </p>
        </div>
        {subscribed ? (
          <button
            onClick={handleUnsubscribe}
            disabled={loading}
            className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? "..." : "Disable"}
          </button>
        ) : (
          <button
            onClick={handleSubscribe}
            disabled={loading}
            className="rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "..." : "Enable"}
          </button>
        )}
      </div>
    </div>
  );
}
