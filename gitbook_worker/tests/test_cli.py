import types
import importlib.util
from pathlib import Path
from gitbook_worker.src.gitbook_worker import docker_cli

MYCLI_PATH = Path(__file__).resolve().parents[2] / "mycli.py"
spec = importlib.util.spec_from_file_location("mycli", MYCLI_PATH)
mycli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mycli)


def test_mycli_invokes_docker(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, check=False):
        calls['cmd'] = cmd
        return types.SimpleNamespace(returncode=0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(docker_cli, 'ensure_docker_desktop', lambda: None)
    monkeypatch.setattr(docker_cli, 'ensure_docker_image', lambda name, path: None)
    monkeypatch.setattr(docker_cli.subprocess, 'run', fake_run)

    mycli.main(['--help'])

    assert calls['cmd'][0] == 'docker'
    assert '-v' in calls['cmd']
    vol_idx = calls['cmd'].index('-v') + 1
    assert calls['cmd'][vol_idx].startswith(str(tmp_path))
    assert docker_cli.IMAGE_NAME in calls['cmd']


def test_mycli_passes_arguments(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, check=False):
        calls['cmd'] = cmd
        return types.SimpleNamespace(returncode=1)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(docker_cli, 'ensure_docker_desktop', lambda: None)
    monkeypatch.setattr(docker_cli, 'ensure_docker_image', lambda name, path: None)
    monkeypatch.setattr(docker_cli.subprocess, 'run', fake_run)

    mycli.main(['--some', 'arg'])

    assert '--some' in calls['cmd']
    assert 'arg' in calls['cmd']
