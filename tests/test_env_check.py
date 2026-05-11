"""
测试 terminalclaw.env_check 模块
"""

import pytest
from unittest.mock import patch, MagicMock

from terminalclaw.env_check import (
    check_tmux,
    check_openclaw,
    check_ollama_cli,
    check_tee,
    check_ollama_service,
    check_ollama_model,
    get_missing_dependencies,
    run_checks,
)


class TestBinaryChecks:
    def test_check_tmux_available(self):
        with patch("shutil.which", return_value="/usr/bin/tmux"):
            assert check_tmux() is True

    def test_check_tmux_missing(self):
        with patch("shutil.which", return_value=None):
            assert check_tmux() is False

    def test_check_openclaw_available(self):
        with patch("shutil.which", return_value="/usr/local/bin/openclaw"):
            assert check_openclaw() is True

    def test_check_openclaw_missing(self):
        with patch("shutil.which", return_value=None):
            assert check_openclaw() is False

    def test_check_ollama_cli_available(self):
        with patch("shutil.which", return_value="/usr/local/bin/ollama"):
            assert check_ollama_cli() is True

    def test_check_ollama_cli_missing(self):
        with patch("shutil.which", return_value=None):
            assert check_ollama_cli() is False

    def test_check_tee_available(self):
        with patch("shutil.which", return_value="/usr/bin/tee"):
            assert check_tee() is True

    def test_check_tee_missing(self):
        with patch("shutil.which", return_value=None):
            assert check_tee() is False


class TestOllamaServiceCheck:
    def test_service_running(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            assert check_ollama_service() is True

    def test_service_not_running_connection_error(self):
        import requests
        with patch("requests.get", side_effect=requests.ConnectionError):
            assert check_ollama_service() is False

    def test_service_timeout(self):
        import requests
        with patch("requests.get", side_effect=requests.Timeout):
            assert check_ollama_service() is False

    def test_service_wrong_status(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("requests.get", return_value=mock_resp):
            assert check_ollama_service() is False


class TestOllamaModelCheck:
    def test_model_found(self):
        result = MagicMock()
        result.stdout = "terminalclaw:latest\nqwen3.5:latest\n"
        with patch("subprocess.run", return_value=result):
            assert check_ollama_model("terminalclaw") is True

    def test_model_not_found(self):
        result = MagicMock()
        result.stdout = "qwen3.5:latest\nllama3:latest\n"
        with patch("subprocess.run", return_value=result):
            assert check_ollama_model("terminalclaw") is False

    def test_ollama_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert check_ollama_model("terminalclaw") is False


class TestMissingDependencies:
    def test_all_present(self):
        with patch("shutil.which", return_value="/usr/bin/mock"):
            assert get_missing_dependencies() == []

    def test_some_missing(self):
        def mock_which(cmd):
            return "/usr/bin/tmux" if cmd == "tmux" else None

        with patch("shutil.which", side_effect=mock_which):
            missing = get_missing_dependencies()
            assert "tmux" not in missing
            assert "openclaw" in missing
            assert "ollama" in missing
            assert "tee" in missing

    def test_all_missing(self):
        with patch("shutil.which", return_value=None):
            missing = get_missing_dependencies()
            assert len(missing) == 4


class TestRunChecks:
    def test_all_good(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        model_result = MagicMock()
        model_result.stdout = "terminalclaw:latest\n"

        with patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("requests.get", return_value=mock_resp), \
             patch("subprocess.run", return_value=model_result):
            result = run_checks("terminalclaw")
            assert result["all_deps_present"] is True
            assert result["ollama_running"] is True
            assert result["ollama_model_ready"] is True

    def test_ollama_down(self):
        import requests
        with patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("requests.get", side_effect=requests.ConnectionError):
            result = run_checks()
            assert result["ollama_running"] is False

    def test_model_missing(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        model_result = MagicMock()
        model_result.stdout = "qwen3.5:latest\n"

        with patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("requests.get", return_value=mock_resp), \
             patch("subprocess.run", return_value=model_result):
            result = run_checks("terminalclaw")
            assert result["ollama_model_ready"] is False
