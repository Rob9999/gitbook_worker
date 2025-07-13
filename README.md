# gitbook_worker

This repository contains a GitBook processing helper written in Python. It is licensed under the MIT license.

## Usage with Docker

Build the Docker image:

```bash
docker build -t gitbook-worker .
```

Run the worker inside the container:

```bash
docker run --rm -v $(pwd):/data gitbook-worker --help
```

Mount your work directories accordingly to process a repository.
