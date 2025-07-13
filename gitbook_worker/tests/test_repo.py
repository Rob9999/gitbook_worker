from gitbook_worker.src.gitbook_worker import repo


def test_clone_force_no_prompt(tmp_path, monkeypatch):
    clone_dir = tmp_path / "repo"
    clone_dir.mkdir()
    (clone_dir / ".git").mkdir()

    calls = []

    def fake_run(cmd, cwd=None, capture_output=False, input_text=None):
        calls.append(cmd)
        return ("", "", 0) if capture_output else None

    monkeypatch.setattr(repo, "run", fake_run)
    prompted = False

    def fake_input(prompt):
        nonlocal prompted
        prompted = True
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)
    repo.clone_or_update_repo("url", str(clone_dir), branch_name="main", force=True)

    assert not prompted
    assert ["git", "-C", str(clone_dir), "fetch", "--all"] in calls


def test_clone_force_reclones_nonrepo(tmp_path, monkeypatch):
    clone_dir = tmp_path / "repo"
    clone_dir.mkdir()

    calls = []

    def fake_run(cmd, cwd=None, capture_output=False, input_text=None):
        calls.append(cmd)
        return ("", "", 0) if capture_output else None

    removed = []
    monkeypatch.setattr(repo, "run", fake_run)
    monkeypatch.setattr(repo, "remove_tree", lambda p: removed.append(p))
    monkeypatch.setattr(
        "builtins.input", lambda p: (_ for _ in ()).throw(Exception("prompted"))
    )

    repo.clone_or_update_repo("url", str(clone_dir), branch_name="main", force=True)

    assert removed == [str(clone_dir)]
    assert any(cmd[:2] == ["git", "clone"] for cmd in calls)
