---
name: dockerfile-conventions
description: Dockerfile patterns, multi-stage builds, and container best practices.
origin: Custom
---
Dockerfile conventions: Use multi-stage builds (build → runtime). Use distroless or alpine for runtime images. Pin base image versions. Minimize layers (chained RUN commands). Use .dockerignore. Prefer COPY over ADD. Activate when writing or reviewing Dockerfiles.
