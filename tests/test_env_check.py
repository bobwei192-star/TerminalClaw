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
    check_cloud_api,
    get_missing_dependencies,
    run_checks,
    is_cloud_mode,
    is_local_mode,
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
        result.stdout = "qwen3.5:latest\nterminalclaw:latest\n"
        with patch("subprocess.run", return_value=result):
            assert check_ollama_model("qwen3.5") is True

    def test_model_not_found(self):
        result = MagicMock()
        result.stdout = "llama3:latest\n"
        with patch("subprocess.run", return_value=result):
            assert check_ollama_model("qwen3.5") is False

    def test_ollama_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert check_ollama_model("qwen3.5") is False


class TestCloudApiCheck:
    def test_api_ok(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("terminalclaw.env_check.DEEPSEEK_API_KEY", "sk-test"), \
             patch("requests.post", return_value=mock_resp):
            assert check_cloud_api() is True

    def test_api_no_key(self):
        with patch("terminalclaw.env_check.DEEPSEEK_API_KEY", ""):
            assert check_cloud_api() is False

    def test_api_connection_error(self):
        import requests
        with patch("terminalclaw.env_check.DEEPSEEK_API_KEY", "sk-test"), \
             patch("requests.post", side_effect=requests.ConnectionError):
            assert check_cloud_api() is False


class TestMissingDependencies:
    def test_all_present_local_mode(self):
        with patch("terminalclaw.env_check.is_local_mode", return_value=True), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=False), \
             patch("shutil.which", return_value="/usr/bin/mock"):
            assert get_missing_dependencies() == []

    def test_ollama_required_in_local_mode(self):
        def mock_which(cmd):
            if cmd in ("tmux", "openclaw", "tee"):
                return "/usr/bin/mock"
            return None

        with patch("terminalclaw.env_check.is_local_mode", return_value=True), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=False), \
             patch("shutil.which", side_effect=mock_which):
            missing = get_missing_dependencies()
            assert "ollama" in missing
            assert "tmux" not in missing

    def test_ollama_not_required_in_cloud_mode(self):
        def mock_which(cmd):
            if cmd in ("tmux", "openclaw", "tee"):
                return "/usr/bin/mock"
            return None

        with patch("terminalclaw.env_check.is_local_mode", return_value=False), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=True), \
             patch("shutil.which", side_effect=mock_which):
            missing = get_missing_dependencies()
            assert "ollama" not in missing


class TestRunChecks:
    def test_local_mode_all_good(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        model_result = MagicMock()
        model_result.stdout = "qwen3.5:latest\n"

        with patch("terminalclaw.env_check.is_local_mode", return_value=True), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=False), \
             patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("requests.get", return_value=mock_resp), \
             patch("subprocess.run", return_value=model_result):
            result = run_checks()
            assert result["mode"] == "local"
            assert result["all_deps_present"] is True
            assert result["ollama_running"] is True
            assert result["ollama_model_ready"] is True

    def test_cloud_mode_all_good(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("terminalclaw.env_check.is_local_mode", return_value=False), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=True), \
             patch("terminalclaw.env_check.DEEPSEEK_API_KEY", "sk-test"), \
             patch("shutil.which", return_value="/usr/bin/mock"), \
             patch("requests.post", return_value=mock_resp):
            result = run_checks()
            assert result["mode"] == "cloud"
            assert result["all_deps_present"] is True
            assert result["cloud_api_ok"] is True

    def test_cloud_mode_missing_key(self):
        with patch("terminalclaw.env_check.is_local_mode", return_value=False), \
             patch("terminalclaw.env_check.is_cloud_mode", return_value=True), \
             patch("terminalclaw.env_check.DEEPSEEK_API_KEY", ""), \
             patch("shutil.which", return_value="/usr/bin/mock"):
            result = run_checks()
            assert result["mode"] == "cloud"
            assert result["cloud_api_key_configured"] is False
            assert result["cloud_api_ok"] is False
