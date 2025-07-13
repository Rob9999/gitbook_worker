import platform
import types
from gitbook_worker.src.gitbook_worker import docker_tools


def test_get_os_matches_platform():
    assert docker_tools.get_os() == platform.system()


def test_ensure_docker_desktop_non_windows(monkeypatch):
    monkeypatch.setattr(docker_tools, "get_os", lambda: "Linux")
    called = {}

    def fake_run(cmd, stdout=None, stderr=None, text=True):
        called["run"] = True
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(docker_tools.subprocess, "run", fake_run)
    docker_tools.ensure_docker_desktop()
    # on non Windows systems docker should not be invoked
    assert "run" not in called


def test_ensure_docker_desktop_starts(monkeypatch):
    monkeypatch.setattr(docker_tools, "get_os", lambda: "Windows")
    runs = {"count": 0}

    def fake_run(cmd, stdout=None, stderr=None, text=True):
        runs["count"] += 1
        # first call fails, second succeeds
        return types.SimpleNamespace(returncode=0 if runs["count"] > 1 else 1)

    popen_called = {}

    class DummyPopen:
        def __init__(self, *a, **kw):
            popen_called["called"] = True

    monkeypatch.setattr(docker_tools.subprocess, "run", fake_run)
    monkeypatch.setattr(docker_tools.os.path, "exists", lambda p: True)
    monkeypatch.setattr(docker_tools.subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(docker_tools.time, "sleep", lambda x: None)

    docker_tools.ensure_docker_desktop()
    assert popen_called.get("called")
    assert runs["count"] >= 2
