#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash docker/build_docker.sh
docker build -f docker_extraimgopt/Dockerfile -t pdfsizeopt:modern-extra .
