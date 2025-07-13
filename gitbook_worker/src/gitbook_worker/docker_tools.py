import os
import subprocess
import sys
import logging
import platform
import time

logger = logging.getLogger(__name__)


def ensure_docker_image(image_name, dockerfile_path) -> None:
    # Prüfe, ob das Image schon existiert
    result = subprocess.run(
        ["docker", "images", "-q", image_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not result.stdout.strip():
        # Baue das Image, falls es nicht existiert
        logger.info("Building Docker image '%s' ...", image_name)
        build_result = subprocess.run(
            [
                "docker",
                "build",
                "-t",
                image_name,
                "-f",
                dockerfile_path,
                os.path.dirname(dockerfile_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if build_result.returncode != 0:
            logger.error("Docker build failed:\n%s", build_result.stderr)
            sys.exit(1)


def get_os() -> str:
    """Return the current operating system name."""
    return platform.system()


def ensure_docker_desktop() -> None:
    """Ensure Docker Desktop is running on Windows."""
    if get_os() != "Windows":
        return

    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return
    except FileNotFoundError:
        logger.error("Docker executable not found")
        return

    docker_path = os.path.expandvars(
        r"%ProgramFiles%\\Docker\\Docker\\Docker Desktop.exe"
    )
    if not os.path.exists(docker_path):
        logger.error("Docker Desktop executable not found: %s", docker_path)
        return

    logger.info("Starting Docker Desktop ...")
    try:
        subprocess.Popen(
            [docker_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("Failed to start Docker Desktop: %s", exc)
        return

    for _ in range(15):  # wait up to ~30 seconds
        time.sleep(2)
        ping = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if ping.returncode == 0:
            logger.info("Docker Desktop started")
            return

    logger.error("Docker Desktop did not start in time")
