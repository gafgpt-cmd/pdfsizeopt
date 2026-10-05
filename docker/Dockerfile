FROM python:3.14.8-slim-trixie@sha256:c3e521df8b2b498a7a682e7e18676771cb80c6b75b8699af886b2d554ce40151
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake pkg-config nasm curl git unzip ca-certificates \
    zlib1g-dev libssl-dev libffi-dev libjpeg-dev libpng-dev libtiff-dev \
    libleptonica-dev libfreetype6-dev libfontconfig1-dev libopenjp2-7-dev \
    liblcms2-dev libbrotli-dev libharfbuzz-dev libcairo2-dev
RUN useradd --system --uid 10001 --user-group --no-create-home \
    --home-dir /work --shell /usr/sbin/nologin pdfsizeopt
WORKDIR /opt/pdfsizeopt
COPY pyproject.toml uv.lock ./
COPY extra/setup_fork_tests.sh extra/
ENV PYTHON3=/usr/local/bin/python3
RUN bash extra/setup_fork_tests.sh
ENV PYTHON3=/opt/pdfsizeopt/.venv/bin/python
COPY . .
RUN .venv/bin/python mksingle.py
USER pdfsizeopt
WORKDIR /work
ENTRYPOINT ["/opt/pdfsizeopt/pdfsizeopt"]
