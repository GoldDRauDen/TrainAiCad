import subprocess

from luan_app.slots import Slots


def git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_ensure_creates_worktree_once(paths):
    s = Slots(paths.repo_root, paths.slots_root)
    p = s.ensure(1)
    assert (p / "rules" / "X.md").is_file()
    assert s.ensure(1) == p
    assert git("worktree", "list", cwd=paths.repo_root).count("slot1") == 1


def test_prepare_checks_out_ref_and_cleans(paths):
    s = Slots(paths.repo_root, paths.slots_root)
    p = s.ensure(1)
    (p / ".work" / "x").mkdir(parents=True)
    (p / "junk.txt").write_text("j")
    (p / "rules" / "X.md").write_text("changed")
    sha, warns = s.prepare(1, "origin/main")
    assert sha == git("rev-parse", "origin/main", cwd=paths.repo_root)
    assert not (p / ".work").exists() and not (p / "junk.txt").exists()
    assert (p / "rules" / "X.md").read_text() == "x\n"
    assert warns == []


def test_prepare_picks_up_new_origin_commit(paths, tmp_path):
    s = Slots(paths.repo_root, paths.slots_root)
    s.ensure(2)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", git("remote", "get-url", "origin", cwd=paths.repo_root), str(clone)], check=True)
    for k, v in {"user.email": "t@t", "user.name": "t"}.items():
        git("config", k, v, cwd=clone)
    (clone / "rules" / "New.md").write_text("n")
    git("add", "-A", cwd=clone)
    git("commit", "-m", "new rule", cwd=clone)
    git("push", "-q", "origin", "main", cwd=clone)
    new = git("rev-parse", "HEAD", cwd=clone)
    sha, _ = s.prepare(2, "origin/main")
    assert sha == new and (s.path(2) / "rules" / "New.md").is_file()


def test_touched_ignores_work_and_reset_cleans(paths):
    s = Slots(paths.repo_root, paths.slots_root)
    p = s.ensure(1)
    s.prepare(1, "origin/main")
    (p / ".work" / "J").mkdir(parents=True)
    (p / ".work" / "J" / "a.json").write_text("{}")
    assert s.touched(1) == []
    (p / "rules" / "X.md").write_text("hacked")
    (p / "tools" / "new.py").write_text("x")
    t = s.touched(1)
    assert any("rules/X.md" in line for line in t) and any("tools/new.py" in line for line in t) and len(t) == 2
    s.reset(1)
    assert s.touched(1) == [] and (p / ".work" / "J" / "a.json").is_file()


def test_main_checkout_untouched(paths):
    s = Slots(paths.repo_root, paths.slots_root)
    p = s.ensure(1)
    s.prepare(1, "origin/main")
    (p / "rules" / "X.md").write_text("hacked")
    s.reset(1)
    assert git("status", "--porcelain", cwd=paths.repo_root) == ""


def test_prepare_fetch_failure_warns(paths):
    s = Slots(paths.repo_root, paths.slots_root)
    s.ensure(1)
    git("remote", "set-url", "origin", str(paths.repo_root / "no-such-remote"), cwd=paths.repo_root)
    sha, warns = s.prepare(1, "origin/main")
    assert sha and warns == ["Không fetch được origin, dùng bản đã có."]
