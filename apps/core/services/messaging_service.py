"""Messaging service — channel management, message sending, reactions, and read tracking."""

import re
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import (
    Channel,
    ChannelMember,
    Message,
    MessageReaction,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _broadcast_message(channel_id: UUID, event: dict) -> None:
    """Broadcast an event to the chat channel group via Channel Layer."""
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"chat_{channel_id}",
                event,
            )
        except Exception:
            pass  # Fail gracefully when Channel Layer not running (e.g., tests)


def _is_member(channel_id: UUID, user_id: int) -> bool:
    """Return True if user is an active member of the channel."""
    return ChannelMember.objects.filter(channel_id=channel_id, user_id=user_id).exists()


def _get_member(channel_id: UUID, user_id: int) -> ChannelMember:
    """Return ChannelMember or raise PermissionError."""
    try:
        return ChannelMember.objects.get(channel_id=channel_id, user_id=user_id)
    except ChannelMember.DoesNotExist:
        raise PermissionError("User is not a member of this channel.") from None


def _extract_mentions(content: str) -> list[str]:
    """Extract @username mentions from message content."""
    return re.findall(r"@(\w+)", content)


# ---------------------------------------------------------------------------
# Channel management
# ---------------------------------------------------------------------------


def create_channel(
    name: str,
    channel_type: str,
    members: list[User],
    created_by: User,
    company,
) -> Channel:
    """Create a channel and add members in a single transaction."""
    with transaction.atomic():
        channel = Channel.objects.create(
            name=name,
            type=channel_type,
            created_by=created_by,
            company=company,
        )
        # Creator gets owner role
        ChannelMember.objects.create(
            channel=channel,
            user=created_by,
            role="owner",
        )
        for member in members:
            if member.pk != created_by.pk:
                ChannelMember.objects.get_or_create(
                    channel=channel,
                    user=member,
                    defaults={"role": "member"},
                )
        return channel


def get_or_create_direct_channel(user1: User, user2: User, company) -> Channel:
    """Find an existing DM channel between two users or create one."""
    with transaction.atomic():
        # Find existing direct channel shared by exactly these two users in this company
        shared = (
            Channel.objects.filter(
                company=company,
                type="direct",
                memberships__user=user1,
            )
            .filter(memberships__user=user2)
            .distinct()
        )
        if shared.exists():
            return shared.first()

        # Create a new DM channel
        name = f"dm_{min(user1.pk, user2.pk)}_{max(user1.pk, user2.pk)}"
        channel = Channel.objects.create(
            name=name,
            type="direct",
            created_by=user1,
            company=company,
        )
        ChannelMember.objects.create(channel=channel, user=user1, role="member")
        ChannelMember.objects.create(channel=channel, user=user2, role="member")
        return channel


def add_member(channel_id: UUID, user_id: UUID, role: str = "member") -> ChannelMember:
    """Add a user to a channel. Idempotent — returns existing membership if found."""
    channel = Channel.objects.get(id=channel_id)
    user = User.objects.get(id=user_id)
    member, _ = ChannelMember.objects.get_or_create(
        channel=channel,
        user=user,
        defaults={"role": role},
    )
    return member


def remove_member(channel_id: UUID, user_id: UUID) -> None:
    """Remove a user from a channel."""
    ChannelMember.objects.filter(channel_id=channel_id, user_id=user_id).delete()


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


def send_message(
    channel_id: UUID,
    sender: User,
    content: str,
    content_type: str = "text",
    reply_to_id: UUID | None = None,
    link_type: str = "",
    link_id: UUID | None = None,
) -> Message:
    """Send a message to a channel.

    Security: verifies sender is a member.
    Detects @mentions and sends notifications.
    """
    _get_member(channel_id, sender.pk)  # raises PermissionError if not member

    with transaction.atomic():
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id, channel_id=channel_id)
            except Message.DoesNotExist:
                pass

        msg = Message.objects.create(
            channel_id=channel_id,
            sender=sender,
            content=content,
            content_type=content_type,
            reply_to=reply_to,
            link_type=link_type or "",
            link_id=link_id,
        )

    # Broadcast to channel group
    _broadcast_message(
        channel_id,
        {
            "type": "chat_message",
            "message": {
                "id": msg.id,
                "channel_id": str(channel_id),
                "sender_id": sender.pk,
                "sender_email": sender.email,
                "content": msg.content,
                "content_type": msg.content_type,
                "reply_to_id": reply_to_id,
                "is_edited": False,
                "is_deleted": False,
                "created_at": msg.created_at.isoformat(),
            },
        },
    )

    # Handle @mentions — send in-app notifications
    mentions = _extract_mentions(content)
    if mentions:
        _notify_mentions(msg, mentions, sender, channel_id)

    return msg


def edit_message(message_id: UUID, content: str, editor: User) -> Message:
    """Edit a message. Only the original sender may edit."""
    with transaction.atomic():
        msg = Message.objects.select_for_update().get(id=message_id)
        if msg.sender_id != editor.pk:
            raise PermissionError("Only the message sender can edit this message.")
        if msg.is_deleted:
            raise ValueError("Cannot edit a deleted message.")
        msg.content = content
        msg.is_edited = True
        msg.edited_at = timezone.now()
        msg.save()

    _broadcast_message(
        msg.channel_id,
        {
            "type": "message_updated",
            "message": {
                "id": msg.id,
                "content": msg.content,
                "is_edited": True,
                "edited_at": msg.edited_at.isoformat(),
            },
        },
    )
    return msg


def delete_message(message_id: UUID, actor: User) -> Message:
    """Soft-delete a message. Sender or channel admin/owner may delete."""
    with transaction.atomic():
        msg = Message.objects.select_for_update().get(id=message_id)

        is_sender = msg.sender_id == actor.pk
        is_channel_admin = ChannelMember.objects.filter(
            channel_id=msg.channel_id,
            user=actor,
            role__in=["admin", "owner"],
        ).exists()

        if not is_sender and not is_channel_admin:
            raise PermissionError(
                "Only the sender or a channel admin can delete this message."
            )

        msg.is_deleted = True
        msg.content = ""  # Clear content on soft-delete
        msg.save()

    _broadcast_message(
        msg.channel_id,
        {
            "type": "message_deleted",
            "message": {"id": msg.id},
        },
    )
    return msg


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------


def add_reaction(message_id: UUID, user_id: UUID, emoji: str) -> dict:
    """Toggle a reaction on a message. Returns {'added': bool}."""
    msg = Message.objects.get(id=message_id)
    # Verify membership
    _get_member(msg.channel_id, user_id)

    user = User.objects.get(id=user_id)
    existing = MessageReaction.objects.filter(
        message=msg, user=user, emoji=emoji
    ).first()
    if existing:
        existing.delete()
        added = False
    else:
        MessageReaction.objects.create(message=msg, user=user, emoji=emoji)
        added = True

    _broadcast_message(
        msg.channel_id,
        {
            "type": "reaction_update",
            "message_id": message_id,
            "emoji": emoji,
            "user_id": user_id,
            "added": added,
        },
    )
    return {"added": added}


def remove_reaction(message_id: UUID, user_id: UUID, emoji: str) -> None:
    """Remove a specific reaction from a message."""
    msg = Message.objects.get(id=message_id)
    _get_member(msg.channel_id, user_id)
    MessageReaction.objects.filter(
        message_id=message_id, user_id=user_id, emoji=emoji
    ).delete()


# ---------------------------------------------------------------------------
# Read tracking
# ---------------------------------------------------------------------------


def mark_read(channel_id: UUID, user_id: UUID, message_id: UUID) -> None:
    """Update the user's last_read_at timestamp for a channel."""
    member = _get_member(channel_id, user_id)
    msg = Message.objects.get(id=message_id, channel_id=channel_id)
    if member.last_read_at < msg.created_at:
        member.last_read_at = msg.created_at
        member.save(update_fields=["last_read_at", "updated_at"])


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def get_channels(user_id: UUID, company_id: UUID) -> list[Channel]:
    """Return all non-archived channels the user is a member of, scoped to company."""
    return list(
        Channel.objects.filter(
            company_id=company_id,
            memberships__user_id=user_id,
            is_archived=False,
        )
        .distinct()
        .order_by("name")
    )


def get_messages(
    channel_id: UUID,
    user: User,
    limit: int = 50,
    before_id: UUID | None = None,
) -> list[Message]:
    """Return paginated messages for a channel. Verifies membership."""
    _get_member(channel_id, user.pk)

    qs = Message.objects.filter(channel_id=channel_id).select_related(
        "sender", "reply_to"
    )
    if before_id:
        qs = qs.filter(id__lt=before_id)
    return list(qs.order_by("-created_at")[:limit])


def get_threads(message_id: UUID) -> list[Message]:
    """Return thread replies to a parent message."""
    return list(
        Message.objects.filter(reply_to_id=message_id)
        .select_related("sender")
        .order_by("created_at")
    )


def search_messages(
    query: str,
    user: User,
    company_id: UUID,
    channel_id: UUID | None = None,
) -> list[Message]:
    """Full-text search (icontains) across messages visible to the user."""
    # Channels the user belongs to in this company
    member_channel_ids = ChannelMember.objects.filter(user=user).values_list(
        "channel_id", flat=True
    )
    qs = Message.objects.filter(
        channel__company_id=company_id,
        channel_id__in=member_channel_ids,
        content__icontains=query,
        is_deleted=False,
    ).select_related("sender", "channel")

    if channel_id:
        qs = qs.filter(channel_id=channel_id)

    return list(qs.order_by("-created_at")[:100])


def get_unread_counts(user_id: UUID, company_id: UUID) -> list[dict]:
    """Return per-channel unread message counts for the user."""
    memberships = ChannelMember.objects.filter(
        user_id=user_id,
        channel__company_id=company_id,
        channel__is_archived=False,
    ).select_related("channel")

    result = []
    for membership in memberships:
        unread = Message.objects.filter(
            channel_id=membership.channel_id,
            created_at__gt=membership.last_read_at,
            is_deleted=False,
        ).count()
        result.append(
            {
                "channel_id": str(membership.channel_id),
                "channel_name": membership.channel.name,
                "unread_count": unread,
            }
        )
    return result


# ---------------------------------------------------------------------------
# System messages
# ---------------------------------------------------------------------------


def send_system_message(
    channel: Channel,
    content: str,
    link_type: str = "",
    link_id: UUID | None = None,
) -> Message:
    """Post a system-generated message to a channel (no sender)."""
    # Use the channel creator as pseudo-sender, fallback to first member
    sender = channel.created_by
    if not sender:
        first_member = channel.memberships.select_related("user").first()
        if not first_member:
            raise ValueError("Channel has no members to act as system sender.")
        sender = first_member.user

    msg = Message.objects.create(
        channel=channel,
        sender=sender,
        content=content,
        content_type="system",
        link_type=link_type or "",
        link_id=link_id,
    )

    _broadcast_message(
        channel.id,
        {
            "type": "chat_message",
            "message": {
                "id": msg.id,
                "channel_id": str(channel.id),
                "sender_id": None,
                "content": msg.content,
                "content_type": "system",
                "is_edited": False,
                "is_deleted": False,
                "created_at": msg.created_at.isoformat(),
            },
        },
    )
    return msg


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _notify_mentions(
    msg: Message, mentions: list[str], sender: User, channel_id: UUID
) -> None:
    """Send in-app notifications for @mentioned users who are channel members."""
    from apps.core.services.notification_service import send_notification

    member_emails = set(
        ChannelMember.objects.filter(channel_id=channel_id).values_list(
            "user__email", flat=True
        )
    )

    for username in mentions:
        # Try to find the mentioned user (match by first part of email or full email)
        qs = User.objects.filter(
            Q(email__iexact=username) | Q(email__istartswith=f"{username}@"),
            is_active=True,
        )
        for mentioned_user in qs:
            if mentioned_user.email in member_emails and mentioned_user.pk != sender.pk:
                send_notification(
                    recipient=mentioned_user,
                    slug="chat_mention",
                    title=f"You were mentioned by {sender.email}",
                    message=msg.content[:200],
                    link=f"/app/messaging/{channel_id}",
                    company=msg.channel.company if hasattr(msg, "channel") else None,
                )
