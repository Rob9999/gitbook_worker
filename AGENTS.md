# Repository Evaluation

This project provides a Python package `gitbook-worker` for processing GitBook repositories. Key observations:

- **License**: The repository is MIT licensed as seen in `LICENSE`.
- **Packaging**: Uses `pyproject.toml` with Python >=3.10 and defines an entry point `gitbook-worker`.
- **Tests**: Contains a comprehensive pytest suite (`gitbook_worker/tests`) with over 60 tests that currently pass.
- **Documentation**: Includes Sphinx docs under `gitbook_worker/docs` and a detailed package README.
- **Docker**: A Dockerfile for the Pandoc build environment exists under `gitbook_worker/src/gitbook_worker`.
- **Root README**: Very brief; Docker usage instructions were missing prior to this sprint.

Overall the project is well structured, but a top-level Docker workflow was not available which meant results could vary between host systems.

# Sprint Plan

1. **Dockerize worker** – Provide a Dockerfile at the repository root so the application can run in a consistent container regardless of the host OS.
2. **Improve documentation** – Expand the root README with build and usage instructions.
3. **CI integration** – Add GitHub Actions workflow running tests and building the Docker image.
4. **Future enhancements** – Consider publishing the image to a registry and adding more usage examples in the docs.

## Sprint 1 goal
Create a root Dockerfile and `.dockerignore` so the gitbook worker can be executed through Docker, ensuring the same environment on every system.
