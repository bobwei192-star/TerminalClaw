"""
测试 terminalclaw.log_manager 模块
"""

import os
import pytest

from terminalclaw.log_manager import (
    setup_log_dir,
    get_log_info,
    rotate_log,
    count_errors,
    read_tail,
    read_grep,
    get_log_summary,
    _format_size,
)


class TestFormatSize:
    def test_bytes(self):
        assert _format_size(0) == "0 B"
        assert _format_size(500) == "500 B"

    def test_kb(self):
        assert _format_size(1024) == "1 KB"
        assert _format_size(1536) == "1 KB"

    def test_mb(self):
        assert _format_size(1048576) == "1 MB"
        assert _format_size(2097152) == "2 MB"

    def test_gb(self):
        assert _format_size(1073741824) == "1 GB"


class TestSetupLogDir:
    def test_creates_dir_and_file(self, temp_dir):
        log_path = setup_log_dir(temp_dir)
        assert os.path.exists(log_path)
        assert os.path.getsize(log_path) == 0

    def test_idempotent(self, temp_dir):
        first = setup_log_dir(temp_dir)
        second = setup_log_dir(temp_dir)
        assert first == second


class TestGetLogInfo:
    def test_file_exists(self, temp_log_file):
        info = get_log_info(temp_log_file)
        assert info["exists"] is True
        assert info["lines"] == 5
        assert info["size_bytes"] > 0

    def test_file_not_exists(self, temp_dir):
        info = get_log_info(os.path.join(temp_dir, "nonexistent.log"))
        assert info["exists"] is False
        assert info["lines"] == 0


class TestRotateLog:
    def test_no_rotation_small_file(self, temp_log_file):
        rotated = rotate_log(temp_log_file, max_mb=1000)
        assert rotated is False
        assert os.path.exists(temp_log_file)

    def test_file_not_exists(self, temp_dir):
        rotated = rotate_log(os.path.join(temp_dir, "nonexistent.log"), max_mb=1)
        assert rotated is False


class TestCountErrors:
    def test_finds_all_error_types(self, temp_log_file):
        count = count_errors(temp_log_file)
        assert count == 2  # ERROR and FATAL, not INFO/WARN

    def test_empty_file(self, temp_dir):
        empty = os.path.join(temp_dir, "empty.log")
        with open(empty, "w") as f:
            f.write("")
        assert count_errors(empty) == 0

    def test_no_errors(self, temp_dir):
        clean = os.path.join(temp_dir, "clean.log")
        with open(clean, "w") as f:
            f.write("INFO Everything ok\nDEBUG Trace data\n")
        assert count_errors(clean) == 0

    def test_file_not_exists(self, temp_dir):
        assert count_errors(os.path.join(temp_dir, "nonexistent.log")) == 0

    def test_critical_and_severe(self, temp_dir):
        log = os.path.join(temp_dir, "critical.log")
        with open(log, "w") as f:
            f.write("CRITICAL Disk full\nSEVERE Memory exhausted\nPANIC Kernel panic\n")
        assert count_errors(log) == 3


class TestReadTail:
    def test_default_lines(self, temp_log_file):
        content = read_tail(temp_log_file, lines=100)
        assert "Starting application" in content
        assert "Shutting down" in content

    def test_limited_lines(self, temp_log_file):
        content = read_tail(temp_log_file, lines=2)
        lines = content.strip().split("\n")
        assert len(lines) == 2

    def test_file_not_exists(self, temp_dir):
        assert read_tail(os.path.join(temp_dir, "nonexistent.log"), lines=10) == ""


class TestReadGrep:
    def test_find_errors(self, temp_log_file):
        content = read_grep(temp_log_file, pattern="ERROR|FATAL")
        assert "Connection failed" in content
        assert "Database unreachable" in content
        assert "Starting application" not in content

    def test_max_lines_limit(self, temp_log_file):
        content = read_grep(temp_log_file, pattern="ERROR|INFO", max_lines=1)
        lines = content.strip().split("\n")
        assert len(lines) == 1

    def test_no_matches(self, temp_log_file):
        content = read_grep(temp_log_file, pattern="NONEXISTENT")
        assert content == ""

    def test_file_not_exists(self, temp_dir):
        assert read_grep(os.path.join(temp_dir, "nonexistent.log"), pattern="ERROR") == ""


class TestGetLogSummary:
    def test_summary_includes_all_fields(self, temp_log_file):
        summary = get_log_summary(temp_log_file)
        assert summary["exists"] is True
        assert summary["lines"] == 5
        assert summary["error_count"] == 2
        assert len(summary["tail_preview"]) > 0
