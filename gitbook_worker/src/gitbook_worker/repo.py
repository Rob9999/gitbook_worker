import logging
import os
import stat
import shutil

from .utils import run


def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: str) -> None:
    try:
        shutil.rmtree(path, onerror=remove_readonly)
    except Exception as e:
        logging.error("Failed to remove directory %s: %s", path, e)
        raise


def checkout_branch(repo_dir: str, branch_name: str) -> None:
    """Check out a specific branch in the given Git repository."""
    try:
        run(["git", "-C", repo_dir, "fetch", "--all"])
        run(["git", "-C", repo_dir, "checkout", branch_name])
        logging.info("Checked out branch: %s", branch_name)
    except SystemExit as e:
        logging.error("Failed to check out branch '%s': Exit code %s", branch_name, e.code)
        raise


def clone_or_update_repo(
    repo_url: str,
    clone_dir: str,
    branch_name: str | None = None,
    force: bool = False,
) -> None:
    if os.path.isdir(clone_dir):
        resp = "y" if force else input(
            f"Directory '{clone_dir}' exists. Clean and reclone? (y/N) "
        ).strip().lower()
        if resp == "y":
            if os.path.isdir(os.path.join(clone_dir, ".git")) and branch_name:
                try:
                    run(["git", "-C", clone_dir, "status"], capture_output=True)
                    logging.info("Valid Git repository found: %s", clone_dir)
                    run(["git", "-C", clone_dir, "fetch", "--all"])
                    run(["git", "-C", clone_dir, "reset", "--hard", f"origin/{branch_name}"])
                    run(["git", "-C", clone_dir, "clean", "-fdx"])
                except SystemExit:
                    logging.warning("Git command failed. Re-cloning repository.")
                    logging.info("Cleaning directory: %s", clone_dir)
                    remove_tree(clone_dir)
                    run(["git", "clone", repo_url, clone_dir])
            else:
                logging.info("Cleaning non-repo directory: %s", clone_dir)
                remove_tree(clone_dir)
                if branch_name:
                    run(["git", "clone", "--branch", branch_name, repo_url, clone_dir])
                else:
                    run(["git", "clone", repo_url, clone_dir])
        else:
            run(["git", "-C", clone_dir, "fetch", "--all"])
            run(["git", "-C", clone_dir, "checkout", branch_name])
            run(["git", "-C", clone_dir, "pull", "origin", branch_name])
    else:
        if branch_name:
            run(["git", "clone", "--branch", branch_name, repo_url, clone_dir])
        else:
            run(["git", "clone", repo_url, clone_dir])

