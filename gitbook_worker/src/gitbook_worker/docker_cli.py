from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .docker_tools import ensure_docker_image, ensure_docker_desktop


IMAGE_NAME = "gitbook-worker"


def main() -> None:
    """Run gitbook-worker inside its Docker container."""
    ensure_docker_desktop()
    root_dir = Path(__file__).resolve().parents[2]
    dockerfile = root_dir / "Dockerfile"
    ensure_docker_image(IMAGE_NAME, str(dockerfile))

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{os.getcwd()}:/data",
        "-w",
        "/data",
        IMAGE_NAME,
    ] + sys.argv[1:]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
