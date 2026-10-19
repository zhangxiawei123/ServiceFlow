"""Exercise actual Chroma filters without downloading an embedding model or calling an API."""

import asyncio
import json
import logging
import uuid
from types import SimpleNamespace

import chromadb
import pytest

from memory.conversation_memory import MemoryManager


class FixedEmbedding:
    def __call__(self, input):
        return [[1.0, 0.0, 0.0] for _ in input]


@pytest.fixture
def memory():
    client = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False))
    manager = MemoryManager.__new__(MemoryManager)
    collections = []
    for field in ["_episodic", "_profile"]:
        collection = client.create_collection("test_" + uuid.uuid4().hex, embedding_function=FixedEmbedding())
        setattr(manager, field, collection)
        collections.append(collection.name)
    yield manager
    for name in collections:
        client.delete_collection(name)


def test_real_chroma_filter_prioritizes_current_session_and_never_leaks_other_users(memory, caplog):
    memory._episodic.add(
        ids=["current", "previous", "duplicate", "other_user"],
        documents=["当前会话摘要", "历史会话摘要", "当前会话摘要", "其他用户秘密"],
        metadatas=[
            {"user_id": "alice", "conv_id": "current"},
            {"user_id": "alice", "conv_id": "previous"},
            {"user_id": "alice", "conv_id": "previous"},
            {"user_id": "bob", "conv_id": "current"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        docs = asyncio.run(memory._search_episodic("alice", "current", "摘要"))
    assert docs == ["当前会话摘要", "历史会话摘要"]
    assert "情景记忆检索失败" not in caplog.text
    assert "Failed to send telemetry" not in caplog.text


def test_empty_collection_and_blank_queries_return_no_history_without_warnings(memory, caplog):
    with caplog.at_level(logging.WARNING):
        assert asyncio.run(memory._search_episodic("alice", "new", "hello")) == []
        assert asyncio.run(memory._search_episodic("alice", "new", "  ")) == []
    assert "情景记忆检索失败" not in caplog.text


def test_current_session_results_stop_at_limit_without_cross_session_fallback(memory):
    memory.HISTORY_TOP_K = 1
    memory._episodic.add(ids=["one", "two"], documents=["当前会话", "历史会话"],
                         metadatas=[{"user_id": "alice", "conv_id": "now"},
                                    {"user_id": "alice", "conv_id": "before"}])
    assert asyncio.run(memory._search_episodic("alice", "now", "会话")) == ["当前会话"]


def test_profile_upsert_replaces_existing_profile_without_delete_warnings(memory, caplog):
    profile = {"preferences": ["中文"], "entities": {}}

    class Messages:
        async def create(self, **kwargs):
            return SimpleNamespace(content=[{"type": "text", "text": json.dumps(profile)}])

    async def messages(*args):
        return [SimpleNamespace(role=SimpleNamespace(value="user"), content="偏好中文")]

    memory._client = SimpleNamespace(messages=Messages())
    memory._model = "test-only"
    memory._get_working_memory = messages
    with caplog.at_level(logging.WARNING):
        asyncio.run(memory.update_profile("alice", "c1"))
        profile["preferences"] = ["英文"]
        asyncio.run(memory.update_profile("alice", "c1"))
    assert memory._profile.count() == 1
    assert asyncio.run(memory._get_profile("alice"))["preferences"] == ["英文"]
    assert "nonexisting" not in caplog.text
    assert "Failed to send telemetry" not in caplog.text
