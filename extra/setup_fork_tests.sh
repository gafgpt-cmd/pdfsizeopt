#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
test "$(uname -sm)" = 'Linux x86_64' || { echo 'Tests require Linux x86_64' >&2; exit 1; }
for tool in curl git cmake make gcc g++ uv qpdf pdftoppm advzip; do
  command -v "$tool" >/dev/null || { echo "Missing test dependency: $tool" >&2; exit 1; }
done
mkdir -p .runtime/bin
download() {
  local target="$1" digest="$2" url="$3"
  if ! test -f "$target"; then
    curl -fL --retry 2 --connect-timeout 10 --max-time 180 -o "$target" "$url"
  fi
  printf '%s  %s\n' "$digest" "$target" | sha256sum -c -
}
if ! test -x pdfsizeopt_libexec/python; then
  download .runtime/libexec-v9.tar.gz \
    d24676a390b8c5ea3a3edcf9af7b69a829537b101df97cc0d08a9998774b68f5 \
    https://github.com/pts/pdfsizeopt/releases/download/2023-04-18/pdfsizeopt_libexec_linux-v9.tar.gz
  tar xzf .runtime/libexec-v9.tar.gz
fi
if ! test -x .runtime/python2/bin/python2.7; then
  download .runtime/Python-2.7.18.tgz \
    da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814 \
    https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz
  tar xzf .runtime/Python-2.7.18.tgz -C .runtime
  (
    cd .runtime/Python-2.7.18
    CFLAGS='-O2 -std=gnu99' ./configure --prefix="$root/.runtime/python2" --without-ensurepip
    make -j4
    make install
  ) > .runtime/python2-build.log 2>&1
fi
if ! test -x .runtime/bin/oxipng; then
  download .runtime/oxipng.tar.gz \
    1813750ef592c5350ca79c88f98b2c0876d05c826dc7156245256d4255c1ad17 \
    https://github.com/oxipng/oxipng/releases/download/v10.2.1/oxipng-10.2.1-x86_64-unknown-linux-musl.tar.gz
  tar xzf .runtime/oxipng.tar.gz -C .runtime
  cp .runtime/oxipng-10.2.1-x86_64-unknown-linux-musl/oxipng .runtime/bin/oxipng
fi
if ! test -x .runtime/bin/ect; then
  if ! test -d .runtime/ect-src/.git; then
    git clone --no-checkout https://github.com/fhanau/Efficient-Compression-Tool.git .runtime/ect-src
  fi
  git -C .runtime/ect-src remote set-url --push origin DISABLED
  git -C .runtime/ect-src checkout --detach 9aabc23d73899ae55c1de292592fed6eb6217f66
  git -C .runtime/ect-src submodule update --init --recursive
  cmake -S .runtime/ect-src/src -B .runtime/ect-build \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  cmake --build .runtime/ect-build -j4
  cp .runtime/ect-build/ect .runtime/bin/ect
fi
if ! test -e .runtime/bin/ECT; then ln -s ect .runtime/bin/ECT; fi
if ! test -x .venv/bin/python; then uv venv --python python3 .venv; fi
uv pip sync --python .venv/bin/python extra/test-requirements.txt
.runtime/python2/bin/python2.7 -c 'import unittest, zlib'
