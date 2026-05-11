import os
import tempfile
import pytest


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def temp_log_file(temp_dir):
    log_path = os.path.join(temp_dir, "test.log")
    with open(log_path, "w") as f:
        f.write("2024-01-01 10:00:00 INFO Starting application\n")
        f.write("2024-01-01 10:00:01 ERROR Connection failed\n")
        f.write("2024-01-01 10:00:02 WARN Retry attempt 1\n")
        f.write("2024-01-01 10:00:03 FATAL Database unreachable\n")
        f.write("2024-01-01 10:00:04 INFO Shutting down\n")
    return log_path


@pytest.fixture
def temp_session_store(temp_dir):
    return os.path.join(temp_dir, "sessions.jsonl")
