"""WebSocket consumers for real-time notifications and chat messaging."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Consumer for sending real-time notifications to authenticated users."""

    async def connect(self):
        # Extract JWT token from query string
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        self.user = None
        if token:
            self.user = await self.get_user_from_token(token)

        if not self.user or self.user.is_anonymous:
            # Fallback to scope user (e.g. session-based if any)
            scope_user = self.scope.get("user")
            if scope_user and not scope_user.is_anonymous:
                self.user = scope_user

        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"notifications_{self.user.id}"

        # Join user group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            # Leave user group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        # Notifications are push-only from server to client
        pass

    async def notification_message(self, event):
        """Send notification message to WebSocket client."""
        await self.send_json(
            {
                "type": "notification_message",
                "notification": event["notification"],
            }
        )

    async def unread_count_update(self, event):
        """Send unread count update to WebSocket client."""
        await self.send_json(
            {"type": "unread_count_update", "unread_count": event["unread_count"]}
        )

    @database_sync_to_async
    def get_user_from_token(self, token):
        from apps.core.models import User

        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
        except Exception:
            return AnonymousUser()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time internal chat messaging."""

    async def connect(self):
        """Authenticate user and join all their channel groups."""
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        self.user = None
        if token:
            self.user = await self.get_user_from_token(token)

        if not self.user or self.user.is_anonymous:
            scope_user = self.scope.get("user")
            if scope_user and not scope_user.is_anonymous:
                self.user = scope_user

        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        # Join all channel groups the user belongs to
        self.channel_groups: list[str] = []
        channel_ids = await self.get_user_channel_ids(self.user)
        for channel_id in channel_ids:
            group_name = f"chat_{channel_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.channel_groups.append(group_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Leave all channel groups cleanly."""
        for group_name in getattr(self, "channel_groups", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content):
        """Route incoming WebSocket messages by type."""
        msg_type = content.get("type")

        if msg_type == "send_message":
            await self.handle_send_message(content)
        elif msg_type == "typing":
            await self.handle_typing(content)
        elif msg_type == "read":
            await self.handle_read(content)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def handle_send_message(self, content: dict):
        """Send a message to a channel via the messaging service."""
        channel_id = content.get("channel_id")
        text = content.get("content", "")
        content_type = content.get("content_type", "text")
        reply_to_id = content.get("reply_to_id")

        if not channel_id or not text:
            await self.send_json(
                {"type": "error", "detail": "channel_id and content required"}
            )
            return

        msg = await self.db_send_message(
            channel_id=channel_id,
            sender=self.user,
            content=text,
            content_type=content_type,
            reply_to_id=reply_to_id,
        )

        if msg is None:
            await self.send_json(
                {"type": "error", "detail": "Not a member of this channel"}
            )

    async def handle_typing(self, content: dict):
        """Broadcast typing indicator to the channel group."""
        channel_id = content.get("channel_id")
        if not channel_id:
            return

        await self.channel_layer.group_send(
            f"chat_{channel_id}",
            {
                "type": "typing_indicator",
                "channel_id": channel_id,
                "user_id": self.user.pk,
                "user_email": self.user.email,
            },
        )

    async def handle_read(self, content: dict):
        """Mark messages as read up to the given message_id."""
        channel_id = content.get("channel_id")
        message_id = content.get("message_id")
        if not channel_id or not message_id:
            return

        await self.db_mark_read(channel_id, self.user.pk, message_id)

    # ------------------------------------------------------------------
    # Channel layer event handlers (group_send → send_json)
    # ------------------------------------------------------------------

    async def chat_message(self, event):
        """Relay a new chat message to the connected client."""
        await self.send_json({"type": "chat_message", "message": event["message"]})

    async def message_updated(self, event):
        """Relay a message edit to the connected client."""
        await self.send_json({"type": "message_updated", "message": event["message"]})

    async def message_deleted(self, event):
        """Relay a message deletion to the connected client."""
        await self.send_json({"type": "message_deleted", "message": event["message"]})

    async def typing_indicator(self, event):
        """Relay a typing indicator to the connected client."""
        # Don't echo back to the sender
        if event.get("user_id") != self.user.pk:
            await self.send_json(
                {
                    "type": "typing",
                    "channel_id": event["channel_id"],
                    "user_id": event["user_id"],
                    "user_email": event["user_email"],
                }
            )

    async def reaction_update(self, event):
        """Relay a reaction update to the connected client."""
        await self.send_json({"type": "reaction_update", **event})

    # ------------------------------------------------------------------
    # Database helpers (sync → async)
    # ------------------------------------------------------------------

    @database_sync_to_async
    def get_user_from_token(self, token):
        from apps.core.models import User

        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
        except Exception:
            return AnonymousUser()

    @database_sync_to_async
    def get_user_channel_ids(self, user) -> list:
        from apps.core.models import ChannelMember

        return list(
            ChannelMember.objects.filter(
                user=user, channel__is_archived=False
            ).values_list("channel_id", flat=True)
        )

    @database_sync_to_async
    def db_send_message(
        self,
        channel_id,
        sender,
        content,
        content_type="text",
        reply_to_id=None,
    ):
        from apps.core.services.messaging_service import send_message

        try:
            return send_message(
                channel_id=channel_id,
                sender=sender,
                content=content,
                content_type=content_type,
                reply_to_id=reply_to_id,
            )
        except PermissionError:
            return None

    @database_sync_to_async
    def db_mark_read(self, channel_id, user_id, message_id):
        from apps.core.services.messaging_service import mark_read

        try:
            mark_read(channel_id=channel_id, user_id=user_id, message_id=message_id)
        except Exception:
            pass
