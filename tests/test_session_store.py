"""
测试 terminalclaw.session_store 模块
"""

import os
import json
import pytest

from terminalclaw.session_store import (
    append_entry,
    read_entries,
    format_entry,
    get_entry_count,
    get_latest_entry,
)


class TestAppendEntry:
    def test_append_single_entry(self, temp_session_store):
        record = format_entry(command="analyze", model="terminalclaw")
        append_entry(temp_session_store, record)

        entries = read_entries(temp_session_store)
        assert len(entries) == 1
        assert entries[0]["command"] == "analyze"

    def test_append_multiple_entries(self, temp_session_store):
        for cmd in ["analyze", "monitor", "start"]:
            append_entry(temp_session_store, format_entry(command=cmd))

        entries = read_entries(temp_session_store)
        assert len(entries) == 3

    def test_append_creates_directory(self, temp_dir):
        store = os.path.join(temp_dir, "subdir", "sessions.jsonl")
        append_entry(store, format_entry(command="test"))
        assert os.path.exists(store)


class TestReadEntries:
    def test_read_empty_file(self, temp_session_store):
        entries = read_entries(temp_session_store)
        assert entries == []

    def test_skip_invalid_json(self, temp_session_store):
        with open(temp_session_store, "w") as f:
            f.write('{"valid": true}\n')
            f.write("not json\n")
            f.write('{"also_valid": true}\n')

        entries = read_entries(temp_session_store)
        assert len(entries) == 2

    def test_read_unicode_entries(self, temp_session_store):
        append_entry(temp_session_store, format_entry(
            command="analyze",
            analysis="检测到 3 个错误：数据库连接失败、内存泄漏、CPU 飙升"
        ))

        entries = read_entries(temp_session_store)
        assert len(entries) == 1
        assert "数据库连接失败" in entries[0]["analysis_summary"]


class TestFormatEntry:
    def test_basic_entry(self):
        entry = format_entry(
            command="analyze",
            model="terminalclaw",
            tokens=1500,
            analysis="发现 2 个 ERROR：连接超时、磁盘空间不足",
        )
        assert entry["command"] == "analyze"
        assert entry["model"] == "terminalclaw"
        assert entry["tokens_used"] == 1500
        assert "timestamp" in entry

    def test_analysis_truncation(self):
        long_analysis = "A" * 1000
        entry = format_entry(command="analyze", analysis=long_analysis)
        assert len(entry["analysis_summary"]) == 500

    def test_extra_fields(self):
        entry = format_entry(
            command="monitor",
            model="qwen3.5",
            extra_field="custom_value",
            another=42,
        )
        assert entry["extra_field"] == "custom_value"
        assert entry["another"] == 42


class TestGetEntryCount:
    def test_empty_store(self, temp_session_store):
        assert get_entry_count(temp_session_store) == 0

    def test_with_entries(self, temp_session_store):
        for _ in range(5):
            append_entry(temp_session_store, format_entry(command="analyze"))
        assert get_entry_count(temp_session_store) == 5


class TestGetLatestEntry:
    def test_empty_store(self, temp_session_store):
        assert get_latest_entry(temp_session_store) is None

    def test_returns_last_entry(self, temp_session_store):
        for i in range(3):
            entry = format_entry(command=f"test_{i}")
            append_entry(temp_session_store, entry)

        latest = get_latest_entry(temp_session_store)
        assert latest["command"] == "test_2"
