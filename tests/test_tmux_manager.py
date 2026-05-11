"""
测试 terminalclaw.tmux_manager 模块
"""

import pytest
from unittest.mock import patch, MagicMock

from terminalclaw.tmux_manager import (
    session_exists,
    create_session,
    kill_session,
    launch_workspace,
    list_panes,
)


class TestSessionExists:
    def test_session_exists(self):
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result):
            assert session_exists("test_session") is True

    def test_session_not_exists(self):
        result = MagicMock()
        result.returncode = 1
        with patch("subprocess.run", return_value=result):
            assert session_exists("test_session") is False


class TestCreateSession:
    def test_create_new_session(self):
        has_session = MagicMock()
        has_session.returncode = 1
        create = MagicMock()
        create.returncode = 0
        check_after = MagicMock()
        check_after.returncode = 0

        with patch("subprocess.run", side_effect=[has_session, create, check_after]):
            assert create_session("test_session") is True

    def test_create_existing_session(self):
        has_session = MagicMock()
        has_session.returncode = 0

        with patch("subprocess.run", return_value=has_session):
            assert create_session("test_session") is False


class TestKillSession:
    def test_kill_existing_session(self):
        has_session = MagicMock()
        has_session.returncode = 0
        kill = MagicMock()
        kill.returncode = 0
        check_after = MagicMock()
        check_after.returncode = 1

        with patch("subprocess.run", side_effect=[has_session, kill, check_after]), \
             patch("time.sleep", return_value=None):
            assert kill_session("test_session") is True

    def test_kill_nonexistent_session(self):
        has_session = MagicMock()
        has_session.returncode = 1

        with patch("subprocess.run", return_value=has_session):
            assert kill_session("test_session") is False


class TestListPanes:
    def test_list_panes_empty(self):
        has_session = MagicMock()
        has_session.returncode = 0
        list_result = MagicMock()
        list_result.returncode = 0
        list_result.stdout = ""

        with patch("subprocess.run", side_effect=[has_session, list_result]):
            panes = list_panes("test_session")
            assert panes == []

    def test_list_panes_with_data(self):
        has_session = MagicMock()
        has_session.returncode = 0
        list_result = MagicMock()
        list_result.returncode = 0
        list_result.stdout = "1|📋 日志输出|12345\n2|🤖 OpenClaw AI|12346"

        with patch("subprocess.run", side_effect=[has_session, list_result]):
            panes = list_panes("test_session")
            assert len(panes) == 2
            assert panes[0]["title"] == "📋 日志输出"
            assert panes[1]["title"] == "🤖 OpenClaw AI"

    def test_list_panes_session_not_exists(self):
        has_session = MagicMock()
        has_session.returncode = 1

        with patch("subprocess.run", return_value=has_session):
            assert list_panes("test_session") == []


class TestLaunchWorkspace:
    def test_launch_new_workspace(self):
        not_exists = MagicMock(returncode=1)
        exists = MagicMock(returncode=0)
        ok = MagicMock(returncode=0)
        get_index = MagicMock(returncode=0)
        get_index.stdout = "2"

        calls = [
            not_exists,  # 1. session_exists(sess) — 不存在
            not_exists,  # 2. create_session 内 session_exists — 不存在
            ok,          # 3. tmux new-session -d
            exists,      # 4. create_session 内 session_exists — 已创建
            ok,          # 5. rename-window
            ok,          # 6. select-pane -T (left)
            ok,          # 7. split-window -h
            get_index,   # 8. display-message #{pane_index}
            ok,          # 9. select-pane -T (right)
        ]

        with patch("subprocess.run", side_effect=calls):
            result = launch_workspace("test_session")
            assert result["ok"] is True
            assert result["left_pane"] == "1.1"
            assert result["right_pane"] == "1.2"

    def test_launch_existing_session(self):
        has_session = MagicMock()
        has_session.returncode = 0

        with patch("subprocess.run", return_value=has_session):
            result = launch_workspace("test_session")
            assert result["ok"] is False
            assert "已存在" in result["error"]
