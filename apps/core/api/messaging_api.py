"""Messaging API — channel management, message CRUD, reactions, search, attachments."""

import logging
from datetime import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.mixins.models import ConcurrencyError
from apps.core.models import Channel, ChannelMember, Message, User
from apps.core.services.messaging_service import (
    add_member,
    add_reaction,
    create_channel,
    delete_message,
    edit_message,
    get_channels,
    get_messages,
    get_or_create_direct_channel,
    get_threads,
    get_unread_counts,
    mark_read,
    remove_member,
    remove_reaction,
    search_messages,
    send_message,
)

logger = logging.getLogger(__name__)
router = Router(auth=JWTAuth())


class ErrorResponse(Schema):
    detail: str


class ChannelOut(Schema):
    id: str
    name: str
    description: str = ""
    type: str
    is_archived: bool = False
    company_id: str
    created_by_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_company_id(obj):
        return str(obj.company_id)

    @staticmethod
    def resolve_created_by_id(obj):
        return str(obj.created_by_id) if obj.created_by_id else None


class ChannelListOut(Schema):
    count: int
    results: list[ChannelOut]


class ChannelCreateIn(Schema):
    name: str
    description: str = ""
    type: str = "public"
    member_ids: list[str] = []


class MemberOut(Schema):
    id: str
    user_id: str
    user_email: str = ""
    role: str
    joined_at: datetime | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_user_id(obj):
        return str(obj.user_id)


class MemberAddIn(Schema):
    user_id: str
    role: str = "member"


class MessageOut(Schema):
    id: str
    channel_id: str
    sender_id: str | None = None
    sender_email: str = ""
    content: str
    content_type: str = "text"
    reply_to_id: str | None = None
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_channel_id(obj):
        return str(obj.channel_id)

    @staticmethod
    def resolve_sender_id(obj):
        return str(obj.sender_id) if obj.sender_id else None

    @staticmethod
    def resolve_reply_to_id(obj):
        return str(obj.reply_to_id) if obj.reply_to_id else None


class MessageListOut(Schema):
    count: int
    results: list[MessageOut]


class SendMessageIn(Schema):
    content: str
    content_type: str = "text"
    reply_to_id: str | None = None


class EditMessageIn(Schema):
    content: str


class ReactionIn(Schema):
    emoji: str


class ReactionOut(Schema):
    added: bool


class UnreadCountOut(Schema):
    channel_id: str
    channel_name: str = ""
    unread_count: int


class SearchResultOut(Schema):
    count: int
    results: list[MessageOut]


class DMChannelOut(Schema):
    id: str
    name: str
    type: str
    company_id: str

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_company_id(obj):
        return str(obj.company_id)


class AttachmentOut(Schema):
    id: str
    file_name: str
    file_size: int
    mime_type: str

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class MarkReadIn(Schema):
    message_id: str


def _get_company_id(request) -> UUID | None:
    company_id = request.headers.get("X-Company-Id")
    if company_id:
        try:
            return UUID(company_id)
        except (ValueError, AttributeError):
            pass
    return None


def _require_company_id(request) -> UUID:
    cid = _get_company_id(request)
    if not cid:
        raise HttpError(400, "X-Company-Id header is required")
    return cid


def _get_channel_or_404(channel_id: UUID, company_id: UUID) -> Channel:
    try:
        return Channel.objects.get(id=channel_id, company_id=company_id)
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None


def _get_message_or_404(message_id: UUID) -> Message:
    try:
        return Message.objects.select_related("channel").get(id=message_id)
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None


# -------------------------------------------------------------------------
# Channels
# -------------------------------------------------------------------------


@router.get("/channels/", response={200: ChannelListOut})
def list_channels(request):
    company_id = _require_company_id(request)
    channels = get_channels(request.auth.id, company_id)
    return {"count": len(channels), "results": channels}


@router.post("/channels/", response={201: ChannelOut, 400: ErrorResponse})
def create_channel_endpoint(request, payload: ChannelCreateIn):
    company_id = _require_company_id(request)

    from apps.core.models import Company

    company = Company.objects.filter(id=company_id).first()
    if not company:
        raise HttpError(400, "Company not found")

    member_ids = [UUID(uid) for uid in payload.member_ids] if payload.member_ids else []
    members = User.objects.filter(id__in=member_ids) if member_ids else []

    try:
        channel = create_channel(
            name=payload.name,
            channel_type=payload.type,
            members=list(members),
            created_by=request.auth,
            company=company,
        )
        return 201, channel
    except Exception as e:
        raise HttpError(400, str(e)) from e


@router.get("/channels/{channel_id}/", response={200: ChannelOut, 404: ErrorResponse})
def get_channel(request, channel_id: UUID):
    company_id = _require_company_id(request)
    channel = _get_channel_or_404(channel_id, company_id)
    return channel


@router.get(
    "/channels/{channel_id}/members/",
    response={200: list[MemberOut], 404: ErrorResponse},
)
def list_members(request, channel_id: UUID):
    company_id = _require_company_id(request)
    channel = _get_channel_or_404(channel_id, company_id)
    members = ChannelMember.objects.filter(channel=channel).select_related("user")
    return list(members)


@router.post(
    "/channels/{channel_id}/members/",
    response={201: MemberOut, 400: ErrorResponse, 404: ErrorResponse},
)
def add_channel_member(request, channel_id: UUID, payload: MemberAddIn):
    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)
    try:
        user_id = UUID(payload.user_id)
        member = add_member(channel_id, user_id, payload.role)
        return 201, member
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    except Exception as e:
        raise HttpError(400, str(e)) from e


@router.delete(
    "/channels/{channel_id}/members/{user_id}/",
    response={200: dict, 404: ErrorResponse},
)
def remove_channel_member(request, channel_id: UUID, user_id: UUID):
    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)
    try:
        remove_member(channel_id, user_id)
        return {"detail": "Member removed"}
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None


# -------------------------------------------------------------------------
# Messages
# -------------------------------------------------------------------------


@router.get(
    "/channels/{channel_id}/messages/",
    response={200: MessageListOut, 404: ErrorResponse},
)
def list_messages(
    request,
    channel_id: UUID,
    limit: int = 50,
    before_id: str | None = None,
):
    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)
    try:
        before_uuid = UUID(before_id) if before_id else None
        messages = get_messages(
            channel_id, request.auth, limit=limit, before_id=before_uuid
        )
        return {"count": len(messages), "results": messages}
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None


@router.post(
    "/channels/{channel_id}/messages/",
    response={
        201: MessageOut,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
)
def create_message(request, channel_id: UUID, payload: SendMessageIn):
    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)
    try:
        reply_to_uuid = UUID(payload.reply_to_id) if payload.reply_to_id else None
        msg = send_message(
            channel_id=channel_id,
            sender=request.auth,
            content=payload.content,
            content_type=payload.content_type,
            reply_to_id=reply_to_uuid,
        )
        return 201, msg
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None
    except Exception as e:
        raise HttpError(400, str(e)) from e


@router.put(
    "/messages/{message_id}/",
    response={
        200: MessageOut,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
)
def update_message(request, message_id: UUID, payload: EditMessageIn):
    _require_company_id(request)
    _get_message_or_404(message_id)
    try:
        msg = edit_message(message_id, payload.content, request.auth)
        return msg
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None
    except ValueError as e:
        raise HttpError(400, str(e)) from e
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e


@router.delete(
    "/messages/{message_id}/",
    response={
        200: dict,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
)
def delete_message_endpoint(request, message_id: UUID):
    _require_company_id(request)
    _get_message_or_404(message_id)
    try:
        delete_message(message_id, request.auth)
        return {"detail": "Message deleted"}
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e


# -------------------------------------------------------------------------
# Reactions
# -------------------------------------------------------------------------


@router.post(
    "/messages/{message_id}/reactions/",
    response={200: ReactionOut, 400: ErrorResponse, 404: ErrorResponse},
)
def add_message_reaction(request, message_id: UUID, payload: ReactionIn):
    _require_company_id(request)
    _get_message_or_404(message_id)
    if not payload.emoji:
        raise HttpError(400, "Emoji is required")
    try:
        result = add_reaction(message_id, request.auth.id, payload.emoji)
        return ReactionOut(**result)
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None
    except PermissionError as e:
        raise HttpError(403, str(e)) from e


@router.delete(
    "/messages/{message_id}/reactions/{emoji}/",
    response={200: dict, 404: ErrorResponse},
)
def remove_message_reaction(request, message_id: UUID, emoji: str):
    _require_company_id(request)
    _get_message_or_404(message_id)
    try:
        remove_reaction(message_id, request.auth.id, emoji)
        return {"detail": "Reaction removed"}
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None
    except PermissionError as e:
        raise HttpError(403, str(e)) from e


# -------------------------------------------------------------------------
# Threads
# -------------------------------------------------------------------------


@router.get(
    "/messages/{message_id}/threads/",
    response={200: MessageListOut, 404: ErrorResponse},
)
def get_message_threads(request, message_id: UUID):
    _require_company_id(request)
    _get_message_or_404(message_id)
    try:
        replies = get_threads(message_id)
        return {"count": len(replies), "results": replies}
    except Message.DoesNotExist:
        raise HttpError(404, "Message not found") from None


# -------------------------------------------------------------------------
# Read tracking
# -------------------------------------------------------------------------


@router.post(
    "/channels/{channel_id}/read/",
    response={200: dict, 403: ErrorResponse, 404: ErrorResponse},
)
def mark_channel_read(request, channel_id: UUID, payload: MarkReadIn):
    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)
    try:
        mark_read(channel_id, request.auth.id, UUID(payload.message_id))
        return {"detail": "Marked as read"}
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except (Channel.DoesNotExist, Message.DoesNotExist):
        raise HttpError(404, "Channel or message not found") from None


@router.get("/unread/", response={200: list[UnreadCountOut]})
def list_unread_counts(request):
    company_id = _require_company_id(request)
    counts = get_unread_counts(request.auth.id, company_id)
    return counts


# -------------------------------------------------------------------------
# Search
# -------------------------------------------------------------------------


@router.get("/search/", response={200: SearchResultOut})
def search_messages_endpoint(
    request,
    q: str,
    channel_id: UUID | None = None,
):
    company_id = _require_company_id(request)
    results = search_messages(q, request.auth, company_id, channel_id)
    return {"count": len(results), "results": results}


# -------------------------------------------------------------------------
# Direct Messages
# -------------------------------------------------------------------------


@router.get("/dm/{user_id}/", response={200: DMChannelOut, 400: ErrorResponse})
def get_or_create_dm(request, user_id: UUID):
    company_id = _require_company_id(request)

    from apps.core.models import Company

    company = Company.objects.filter(id=company_id).first()
    if not company:
        raise HttpError(400, "Company not found")

    try:
        target_user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None

    if target_user.id == request.auth.id:
        raise HttpError(400, "Cannot create DM with yourself")

    channel = get_or_create_direct_channel(request.auth, target_user, company)
    return channel


# -------------------------------------------------------------------------
# Attachments
# -------------------------------------------------------------------------


@router.post(
    "/channels/{channel_id}/attachments/",
    response={
        200: AttachmentOut,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
)
def upload_attachment(request, channel_id: UUID):
    from apps.core.models import MessageAttachment

    company_id = _require_company_id(request)
    _get_channel_or_404(channel_id, company_id)

    file = request.FILES.get("file")
    if not file:
        raise HttpError(400, "No file provided")

    try:
        msg = send_message(
            channel_id=channel_id,
            sender=request.auth,
            content=file.name,
            content_type="file",
        )
        attachment = MessageAttachment.objects.create(
            message=msg,
            file=file,
            file_name=file.name,
            file_size=file.size,
            mime_type=file.content_type or "application/octet-stream",
        )
        return attachment
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except Channel.DoesNotExist:
        raise HttpError(404, "Channel not found") from None
    except Exception as e:
        raise HttpError(400, str(e)) from e
