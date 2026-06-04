"""Tests for internal messaging system (T019a) — models, service, API."""

from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja.testing import TestClient

from apps.core.api import router
from apps.core.models import (
    Channel,
    ChannelMember,
    Company,
    Message,
    MessageAttachment,
    MessageReaction,
    MessageRead,
    User,
)
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
    send_system_message,
)

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company():
    return Company.objects.create(name="Test Corp", code="TC")


@pytest.fixture
def user(company):
    return User.objects.create_user(
        email="alice@test.com",
        password="pass123",
        full_name="Alice",
        current_company=company,
    )


@pytest.fixture
def other_user(company):
    return User.objects.create_user(
        email="bob@test.com",
        password="pass123",
        full_name="Bob",
        current_company=company,
    )


@pytest.fixture
def third_user(company):
    return User.objects.create_user(
        email="charlie@test.com",
        password="pass123",
        full_name="Charlie",
        current_company=company,
    )


@pytest.fixture
def channel(company, user):
    return create_channel(
        name="general",
        channel_type="public",
        members=[user],
        created_by=user,
        company=company,
    )


@pytest.fixture
def client(user):
    from rest_framework_simplejwt.tokens import AccessToken

    token = str(AccessToken.for_user(user))
    c = TestClient(router)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestChannelModel:
    def test_create_channel(self, channel):
        assert channel.name == "general"
        assert channel.type == "public"
        assert channel.is_archived is False
        assert str(channel) == f"public - general ({channel.company.code})"

    def test_channel_str_dm(self, company, user):
        c = Channel.objects.create(
            name="dm_1_2",
            type="direct",
            created_by=user,
            company=company,
        )
        assert "direct - dm_1_2" in str(c)


class TestChannelMemberModel:
    def test_member_created(self, channel, user):
        member = ChannelMember.objects.get(channel=channel, user=user)
        assert member.role == "owner"
        assert str(member) == f"{user.email} in {channel.name}"

    def test_unique_together(self, channel, user):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ChannelMember.objects.create(channel=channel, user=user, role="member")


class TestMessageModel:
    def test_create_message(self, channel, user):
        msg = Message.objects.create(
            channel=channel,
            sender=user,
            content="Hello world",
        )
        assert msg.content == "Hello world"
        assert msg.content_type == "text"
        assert msg.is_edited is False
        assert msg.is_deleted is False
        assert str(msg) == f"Msg {msg.id} by {user.email} in {channel.name}"

    def test_reply_to(self, channel, user):
        parent = Message.objects.create(channel=channel, sender=user, content="Parent")
        reply = Message.objects.create(
            channel=channel,
            sender=user,
            content="Reply",
            reply_to=parent,
        )
        assert reply.reply_to == parent

    def test_soft_delete(self, channel, user):
        msg = Message.objects.create(channel=channel, sender=user, content="Delete me")
        msg.is_deleted = True
        msg.content = ""
        msg.save()
        deleted = Message.objects.get(id=msg.id)
        assert deleted.is_deleted is True
        assert deleted.content == ""


class TestMessageAttachmentModel:
    def test_create_attachment(self, channel, user):
        msg = Message.objects.create(channel=channel, sender=user, content="file.txt")
        att = MessageAttachment.objects.create(
            message=msg,
            file="chat_attachments/test.txt",
            file_name="test.txt",
            file_size=1024,
            mime_type="text/plain",
        )
        assert att.file_name == "test.txt"
        assert str(att) == "test.txt"


class TestMessageReactionModel:
    def test_toggle_reaction(self, channel, user):
        msg = Message.objects.create(channel=channel, sender=user, content="React")
        r = MessageReaction.objects.create(message=msg, user=user, emoji="👍")
        assert str(r) == f"{user.email} reacts 👍 to message {msg.id}"
        assert MessageReaction.objects.filter(
            message=msg, user=user, emoji="👍"
        ).exists()

    def test_unique_reaction(self, channel, user):
        from django.db import IntegrityError

        msg = Message.objects.create(channel=channel, sender=user, content="React")
        MessageReaction.objects.create(message=msg, user=user, emoji="👍")
        with pytest.raises(IntegrityError):
            MessageReaction.objects.create(message=msg, user=user, emoji="👍")


class TestMessageReadModel:
    def test_read_record(self, channel, user):
        msg = Message.objects.create(channel=channel, sender=user, content="Read me")
        read = MessageRead.objects.create(message=msg, user=user)
        assert str(read) == f"Message {msg.id} read by {user.email}"

    def test_unique_read(self, channel, user):
        from django.db import IntegrityError

        msg = Message.objects.create(channel=channel, sender=user, content="Read")
        MessageRead.objects.create(message=msg, user=user)
        with pytest.raises(IntegrityError):
            MessageRead.objects.create(message=msg, user=user)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestCreateChannel:
    def test_creates_channel_with_owner(self, company, user, other_user):
        ch = create_channel(
            name="dev",
            channel_type="private",
            members=[user, other_user],
            created_by=user,
            company=company,
        )
        assert ch.name == "dev"
        assert ch.type == "private"
        members = ChannelMember.objects.filter(channel=ch)
        assert members.count() == 2
        owner = members.get(user=user)
        assert owner.role == "owner"
        member_role = members.get(user=other_user)
        assert member_role.role == "member"

    def test_creates_without_members(self, company, user):
        ch = create_channel(
            name="empty",
            channel_type="public",
            members=[],
            created_by=user,
            company=company,
        )
        assert ChannelMember.objects.filter(channel=ch).count() == 1


class TestDirectChannel:
    def test_get_or_create_dm(self, company, user, other_user):
        dm = get_or_create_direct_channel(user, other_user, company)
        assert dm.type == "direct"
        assert ChannelMember.objects.filter(channel=dm).count() == 2

    def test_dm_is_reused(self, company, user, other_user):
        dm1 = get_or_create_direct_channel(user, other_user, company)
        dm2 = get_or_create_direct_channel(user, other_user, company)
        assert dm1.id == dm2.id


class TestAddRemoveMember:
    def test_add_member(self, channel, other_user):
        member = add_member(channel.id, other_user.id)
        assert member.user == other_user
        assert member.role == "member"

    def test_add_member_idempotent(self, channel, other_user):
        add_member(channel.id, other_user.id)
        add_member(channel.id, other_user.id)
        assert ChannelMember.objects.filter(channel=channel).count() == 2

    def test_remove_member(self, channel, other_user):
        add_member(channel.id, other_user.id)
        remove_member(channel.id, other_user.id)
        assert not ChannelMember.objects.filter(
            channel=channel, user=other_user
        ).exists()

    def test_remove_non_member_does_not_error(self, channel, other_user):
        remove_member(channel.id, other_user.id)  # should not raise


class TestSendMessage:
    def test_send_message(self, channel, user):
        msg = send_message(
            channel_id=channel.id,
            sender=user,
            content="Hello!",
        )
        assert msg.content == "Hello!"
        assert msg.sender == user
        assert msg.content_type == "text"

    def test_send_non_member_raises(self, channel, other_user):
        with pytest.raises(PermissionError):
            send_message(
                channel_id=channel.id,
                sender=other_user,
                content="Should fail",
            )

    def test_send_reply(self, channel, user):
        parent = send_message(channel_id=channel.id, sender=user, content="Parent")
        reply = send_message(
            channel_id=channel.id,
            sender=user,
            content="Reply",
            reply_to_id=parent.id,
        )
        assert reply.reply_to_id == parent.id

    def test_mention_detection(self, channel, user, other_user):
        add_member(channel.id, other_user.id)
        msg = send_message(
            channel_id=channel.id,
            sender=user,
            content="Hey @bob look at this",
        )
        assert msg.content == "Hey @bob look at this"


class TestEditMessage:
    def test_edit_own_message(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="Original")
        edited = edit_message(msg.id, "Updated", user)
        assert edited.content == "Updated"
        assert edited.is_edited is True

    def test_edit_others_message_raises(self, channel, user, other_user):
        msg = send_message(channel_id=channel.id, sender=user, content="Original")
        with pytest.raises(PermissionError):
            edit_message(msg.id, "Hacked", other_user)

    def test_edit_deleted_raises(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="To delete")
        delete_message(msg.id, user)
        with pytest.raises(ValueError):
            edit_message(msg.id, "Edited after delete", user)


class TestDeleteMessage:
    def test_delete_own_message(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="Delete me")
        deleted = delete_message(msg.id, user)
        assert deleted.is_deleted is True

    def test_delete_others_message_raises(self, channel, user, other_user):
        msg = send_message(channel_id=channel.id, sender=user, content="Mine")
        with pytest.raises(PermissionError):
            delete_message(msg.id, other_user)

    def test_admin_can_delete(self, channel, user, other_user):
        add_member(channel.id, other_user.id, role="admin")
        msg = send_message(channel_id=channel.id, sender=user, content="By admin")
        delete_message(msg.id, other_user)  # should not raise


class TestReactions:
    def test_add_reaction(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="React")
        result = add_reaction(msg.id, user.id, "👍")
        assert result["added"] is True

    def test_remove_reaction_on_toggle(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="Toggle")
        add_reaction(msg.id, user.id, "👍")
        result = add_reaction(msg.id, user.id, "👍")
        assert result["added"] is False

    def test_remove_reaction(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="React")
        add_reaction(msg.id, user.id, "👍")
        remove_reaction(msg.id, user.id, "👍")
        assert not MessageReaction.objects.filter(
            message=msg, user=user, emoji="👍"
        ).exists()


class TestReadTracking:
    def test_mark_read(self, channel, user, other_user):
        add_member(channel.id, other_user.id)
        msg = send_message(channel_id=channel.id, sender=user, content="Read me")
        mark_read(channel.id, other_user.id, msg.id)
        member = ChannelMember.objects.get(channel=channel, user=other_user)
        assert member.last_read_at >= msg.created_at

    def test_unread_counts(self, channel, user, other_user):
        add_member(channel.id, other_user.id)
        send_message(channel_id=channel.id, sender=user, content="Msg 1")
        send_message(channel_id=channel.id, sender=user, content="Msg 2")
        counts = get_unread_counts(other_user.id, channel.company_id)
        channel_count = next(
            (c for c in counts if c["channel_id"] == str(channel.id)), None
        )
        assert channel_count is not None
        assert channel_count["unread_count"] == 2


class TestGetMessages:
    def test_get_messages(self, channel, user):
        for i in range(5):
            send_message(channel_id=channel.id, sender=user, content=f"Msg {i}")
        msgs = get_messages(channel.id, user)
        assert len(msgs) == 5

    def test_pagination(self, channel, user):
        for i in range(10):
            send_message(channel_id=channel.id, sender=user, content=f"Msg {i}")
        msgs = get_messages(channel.id, user, limit=3)
        assert len(msgs) == 3

    def test_before_id(self, channel, user):
        ids = []
        for i in range(5):
            msg = send_message(channel_id=channel.id, sender=user, content=f"Msg {i}")
            ids.append(msg.id)
        msgs = get_messages(channel.id, user, limit=10, before_id=ids[3])
        assert all(m.id < ids[3] for m in msgs)

    def test_non_member_raises(self, channel, other_user):
        with pytest.raises(PermissionError):
            get_messages(channel.id, other_user)


class TestThreads:
    def test_get_threads(self, channel, user):
        parent = send_message(channel_id=channel.id, sender=user, content="Parent")
        send_message(
            channel_id=channel.id, sender=user, content="Reply 1", reply_to_id=parent.id
        )
        send_message(
            channel_id=channel.id, sender=user, content="Reply 2", reply_to_id=parent.id
        )
        replies = get_threads(parent.id)
        assert len(replies) == 2


class TestSearch:
    def test_search(self, channel, user):
        send_message(channel_id=channel.id, sender=user, content="Invoice PO-00123")
        send_message(
            channel_id=channel.id, sender=user, content="Purchase order for supplies"
        )
        results = search_messages("invoice", user, channel.company_id)
        assert len(results) == 1

    def test_search_no_results(self, channel, user):
        send_message(channel_id=channel.id, sender=user, content="Hello")
        results = search_messages("nonexistent", user, channel.company_id)
        assert len(results) == 0

    def test_search_filters_deleted(self, channel, user):
        msg = send_message(channel_id=channel.id, sender=user, content="Delete this")
        delete_message(msg.id, user)
        results = search_messages("Delete", user, channel.company_id)
        assert len(results) == 0

    def test_non_member_cannot_see(self, channel, user, other_user, company):
        other_channel = create_channel(
            name="secret",
            channel_type="private",
            members=[other_user],
            created_by=other_user,
            company=company,
        )
        send_message(
            channel_id=other_channel.id, sender=other_user, content="Secret msg"
        )
        results = search_messages("Secret", user, channel.company_id)
        assert len(results) == 0


class TestGetChannels:
    def test_get_channels(self, channel, user, company):
        ch2 = create_channel(
            name="random",
            channel_type="public",
            members=[user],
            created_by=user,
            company=company,
        )
        channels = get_channels(user.id, company.id)
        assert len(channels) == 2
        assert {c.id for c in channels} == {channel.id, ch2.id}

    def test_excludes_archived(self, channel, user, company):
        channel.is_archived = True
        channel.save()
        channels = get_channels(user.id, company.id)
        assert len(channels) == 0

    def test_excludes_non_member(self, channel, user, other_user, company):
        channels = get_channels(other_user.id, company.id)
        assert len(channels) == 0


class TestSystemMessage:
    def test_send_system_message(self, channel, user):
        msg = send_system_message(channel, "System alert")
        assert msg.content == "System alert"
        assert msg.content_type == "system"


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


def _cid(channel):
    return {"X-Company-Id": str(channel.company_id)}


class TestChannelsAPI:
    LIST_URL = "/messaging/channels/"

    def test_list_channels(self, client, channel):
        resp = client.get(self.LIST_URL, headers=_cid(channel))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any(c["name"] == "general" for c in data["results"])

    def test_list_requires_company(self, client):
        resp = client.get(self.LIST_URL)
        assert resp.status_code == 400

    def test_create_channel(self, client, company, other_user):
        resp = client.post(
            self.LIST_URL,
            json={
                "name": "new-channel",
                "type": "public",
                "member_ids": [str(other_user.id)],
            },
            headers={"X-Company-Id": str(company.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "new-channel"

    def test_get_channel_detail(self, client, channel):
        resp = client.get(f"{self.LIST_URL}{channel.id}/", headers=_cid(channel))
        assert resp.status_code == 200
        assert resp.json()["name"] == "general"

    def test_get_channel_not_found(self, client, channel):
        resp = client.get(f"{self.LIST_URL}{uuid4()}/", headers=_cid(channel))
        assert resp.status_code == 404


class TestMembersAPI:
    def test_list_members(self, client, channel, user):
        resp = client.get(
            f"/messaging/channels/{channel.id}/members/", headers=_cid(channel)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(m["user_id"] == str(user.id) for m in data)

    def test_add_member(self, client, channel, other_user):
        resp = client.post(
            f"/messaging/channels/{channel.id}/members/",
            json={"user_id": str(other_user.id), "role": "member"},
            headers=_cid(channel),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "member"

    def test_remove_member(self, client, channel, other_user):
        from apps.core.services.messaging_service import add_member

        add_member(channel.id, other_user.id)
        resp = client.delete(
            f"/messaging/channels/{channel.id}/members/{other_user.id}/",
            headers=_cid(channel),
        )
        assert resp.status_code == 200


class TestMessagesAPI:
    def test_send_message(self, client, channel):
        resp = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "API test message"},
            headers=_cid(channel),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "API test message"

    def test_list_messages(self, client, channel):
        client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Msg 1"},
            headers=_cid(channel),
        )
        resp = client.get(
            f"/messaging/channels/{channel.id}/messages/", headers=_cid(channel)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1

    def test_edit_message(self, client, channel):
        create = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Original"},
            headers=_cid(channel),
        )
        msg_id = create.json()["id"]
        resp = client.put(
            f"/messaging/messages/{msg_id}/",
            json={"content": "Edited"},
            headers=_cid(channel),
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Edited"

    def test_delete_message(self, client, channel):
        create = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Delete me"},
            headers=_cid(channel),
        )
        msg_id = create.json()["id"]
        resp = client.delete(f"/messaging/messages/{msg_id}/", headers=_cid(channel))
        assert resp.status_code == 200


class TestReactionsAPI:
    def test_add_reaction(self, client, channel):
        create = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "React"},
            headers=_cid(channel),
        )
        msg_id = create.json()["id"]
        resp = client.post(
            f"/messaging/messages/{msg_id}/reactions/",
            json={"emoji": "🔥"},
            headers=_cid(channel),
        )
        assert resp.status_code == 200
        assert resp.json()["added"] is True

    def test_remove_reaction(self, client, channel):
        create = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "React"},
            headers=_cid(channel),
        )
        msg_id = create.json()["id"]
        client.post(
            f"/messaging/messages/{msg_id}/reactions/",
            json={"emoji": "🔥"},
            headers=_cid(channel),
        )
        resp = client.delete(
            f"/messaging/messages/{msg_id}/reactions/%F0%9F%94%A5/",
            headers=_cid(channel),
        )
        assert resp.status_code == 200


class TestThreadsAPI:
    def test_get_threads(self, client, channel):
        parent = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Parent"},
            headers=_cid(channel),
        ).json()
        client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Reply", "reply_to_id": parent["id"]},
            headers=_cid(channel),
        )
        resp = client.get(
            f"/messaging/messages/{parent['id']}/threads/", headers=_cid(channel)
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestReadAPI:
    def test_mark_read(self, client, channel):
        msg = client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Read me"},
            headers=_cid(channel),
        ).json()
        resp = client.post(
            f"/messaging/channels/{channel.id}/read/",
            json={"message_id": msg["id"]},
            headers=_cid(channel),
        )
        assert resp.status_code == 200


class TestUnreadAPI:
    def test_unread_counts(self, client, channel, company):
        client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Unread msg"},
        )
        resp = client.get(
            "/messaging/unread/",
            headers={"X-Company-Id": str(company.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["channel_id"] == str(channel.id) for c in data)


class TestSearchAPI:
    def test_search(self, client, channel):
        client.post(
            f"/messaging/channels/{channel.id}/messages/",
            json={"content": "Special report Q4"},
            headers=_cid(channel),
        )
        resp = client.get(
            "/messaging/search/?q=Special",
            headers={"X-Company-Id": str(channel.company_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_search_requires_q(self, client):
        resp = client.get(
            "/messaging/search/",
            headers={"X-Company-Id": str(uuid4())},
        )
        assert resp.status_code == 422


class TestDMAPI:
    def test_get_or_create_dm(self, client, other_user, company):
        resp = client.get(
            f"/messaging/dm/{other_user.id}/",
            headers={"X-Company-Id": str(company.id)},
        )
        assert resp.status_code == 200
        assert resp.json()["type"] == "direct"

    def test_dm_with_self_fails(self, client, user, company):
        resp = client.get(
            f"/messaging/dm/{user.id}/",
            headers={"X-Company-Id": str(company.id)},
        )
        assert resp.status_code == 400


class TestAttachmentsAPI:
    def test_upload_attachment(self, client, channel, user, db):
        from django.test.client import Client as DjangoClient
        from rest_framework_simplejwt.tokens import AccessToken

        django_client = DjangoClient()
        token = str(AccessToken.for_user(user))
        f = SimpleUploadedFile("test.txt", b"file content", content_type="text/plain")
        resp = django_client.post(
            f"/api/v1/core/messaging/channels/{channel.id}/attachments/",
            {"file": f},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_COMPANY_ID=str(channel.company_id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_name"] == "test.txt"
