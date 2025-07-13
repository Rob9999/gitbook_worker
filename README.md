# gitbook_worker (in development)

This repository contains a GitBook processing helper written in Python. It is licensed under the MIT license.

## Usage with Docker

The repository includes a `Dockerfile` at the project root. It creates a
minimal environment with Pandoc and TeXLive so the worker can run
consistently on any host. The accompanying `.dockerignore` file excludes
unnecessary sources from the build context.

Build the container image:

```bash
docker build -t gitbook-worker .
```

Run the worker inside the container:

```bash
docker run --rm -v $(pwd):/data gitbook-worker --help
```

You can also install the package locally and use the helper script
`gitbook-worker-docker`. It builds the image if needed and runs the worker in the
container while mounting the current directory:

```bash
pip install -e gitbook_worker
gitbook-worker-docker --help
```

Mount your working directories as needed to process a GitBook repository.
