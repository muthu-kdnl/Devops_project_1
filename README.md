# Core Ops API

A production-grade, hardened REST API built with FastAPI, packaged with multi-stage Docker builds, and delivered through an automated GitHub Actions CI/CD pipeline integrated with Trivy vulnerability scanning, Hadolint linting, and GitHub Container Registry (GHCR).

---

## Architecture Overview

```text
[ Developer Machine ]
        │
        ▼ (git push)
[ GitHub Repository ]
        │
        ├──► Trigger: GitHub Actions Runner (Ubuntu Latest)
        │       │
        │       ├── Step 1: Linting & Static Code Analysis (Hadolint)
        │       ├── Step 2: Multi-stage Docker Build (Buildx + Cache)
        │       ├── Step 3: Container Vulnerability Scan (Trivy)
        │       └── Step 4: Secure Push via OIDC / GITHUB_TOKEN
        │
        ▼
[ GitHub Container Registry (ghcr.io) ]
        │
        ▼ (docker pull & run)
[ Target Runtime / Local Docker Host ]
        │
        ▼ (curl / HTTP Request)
[ FastAPI Container (Non-root, Read-only FS, Resource-constrained) ]
```

---

## Features & Production Guardrails

- **Hardened Multi-Stage Dockerfile**: Builds wheels in an ephemeral compilation stage; ships only lean runtime assets to the final container (`python:3.12-slim`).
- **Non-Root Execution**: Runs under a dedicated service account (`appuser:appgroup`, UID/GID `10001`) with `/sbin/nologin`.
- **Runtime Enforcements**: Designed to run with dropped Linux capabilities (`--cap-drop=ALL`), read-only root filesystem (`--read-only`), and `no-new-privileges:true`.
- **CI/CD Security Gates**:
  - **Hadolint**: Validates Dockerfile syntax and security anti-patterns.
  - **Trivy**: Scans container layers and Python virtual environment for `HIGH` and `CRITICAL` unfixed CVEs. Builds fail automatically upon detection.
  - **Least Privilege Tokens**: Workflow uses restricted `GITHUB_TOKEN` permissions (`contents: read`, `packages: write`).
- **Native Health Checks**: Container-level and HTTP-level `/healthz` endpoints for orchestrator probes.

---

## Repository Structure

```text
.
├── .dockerignore                 # Excludes local files from Docker context
├── .github/
│   └── workflows/
│       └── ci-cd.yml             # GitHub Actions lint, build, scan, and push pipeline
├── Dockerfile                    # Hardened multi-stage container specification
├── README.md                     # Project documentation
├── app/
│   ├── __init__.py               # Python package initialization
│   └── main.py                   # FastAPI application source & endpoints
└── requirements.txt              # Pinned application dependencies
```

---

## Quickstart & Local Development

### Prerequisites
- Python 3.12+
- Docker Engine 24.0+ (with BuildKit enabled)
- `curl` (for health check testing)

### 1. Run Locally (Without Docker)

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start API server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Test endpoints:
```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/api/v1/info
```

---

## Container Build & Hardened Runtime

### 1. Build the Container

Use Docker BuildKit for layer caching:

```bash
DOCKER_BUILDKIT=1 docker build -t core-ops-api:1.0.0 .
```

### 2. Run with Enterprise Hardening Flags

Run the container using production security constraints:

```bash
docker run -d \
  --name core-ops-app \
  -p 8000:8000 \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  --memory="256m" \
  --cpus="0.5" \
  core-ops-api:1.0.0
```

| Flag | Purpose |
| :--- | :--- |
| `--read-only` | Mounts the container root filesystem as read-only, preventing runtime payload writes or tampering. |
| `--cap-drop=ALL` | Strips all default Linux kernel capabilities (e.g., `CAP_CHOWN`, `CAP_NET_ADMIN`, `CAP_SYS_ADMIN`). |
| `--security-opt=no-new-privileges:true` | Prevents sub-processes from acquiring additional privileges via setuid/setgid binaries. |
| `--memory="256m"` / `--cpus="0.5"` | Enforces cgroup limits to protect the host against resource exhaustion or noisy neighbor issues. |

---

## Verification & Security Testing

### 1. Verify Application Health

```bash
# Verify HTTP 200 response
curl -i http://127.0.0.1:8000/healthz

# Verify Docker daemon healthcheck status
docker inspect --format='{{json .State.Health.Status}}' core-ops-app
```

Expected output: `"healthy"`

### 2. Verify Non-Root User Execution

```bash
docker top core-ops-app
```
Confirm the running process UID matches `10001` (or `appuser`), not `root` / `UID 0`.

### 3. Verify Read-Only Root Filesystem

Attempt to write a file into the running container:

```bash
docker exec core-ops-app touch /app/exploit.txt
```

Expected output:
```text
touch: /app/exploit.txt: Read-only file system
```

---

## CI/CD Pipeline & Automated Registry Publishing

The GitHub Actions workflow at `.github/workflows/ci-cd.yml` automates verification and deployment:

1. **Lint Phase**:
   - Executes `hadolint/hadolint-action` against the `Dockerfile`.
2. **Build Phase**:
   - Configures Buildx and GitHub Actions cache backend.
   - Builds temporary local scan target image.
3. **Scan Phase (Trivy)**:
   - Scans container layers and libraries with `aquasecurity/trivy-action`.
   - Fails the pipeline (`exit-code: 1`) if any unfixed `HIGH` or `CRITICAL` vulnerabilities exist.
4. **Publish Phase (GHCR)**:
   - Logs into `ghcr.io` via ephemeral `${{ secrets.GITHUB_TOKEN }}`.
   - Tags the image with both commit SHA (`sha-<short_sha>`) and `latest` (on main branch merges).
   - Pushes the immutable image artifact to GitHub Packages.

---

## Clean Up

```bash
docker stop core-ops-app
docker rm core-ops-app
```