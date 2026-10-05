#!/bin/bash
set -euo pipefail
download() {
  local target="$1" digest="$2" url="$3"
  if printf '%s  %s\n' "$digest" "$target" | sha256sum -c --status - 2>/dev/null; then
    return
  fi
  curl -fL --retry 2 --connect-timeout 10 --max-time 600 -o "$target.part" "$url"
  printf '%s  %s\n' "$digest" "$target.part" | sha256sum -c -
  mv -f "$target.part" "$target"
}
checkout() {
  local directory="$1" repository="$2" revision="$3"
  if ! test -d "$directory/.git"; then git clone --no-checkout "$repository" "$directory"; fi
  git -C "$directory" remote set-url --push origin DISABLED
  git -C "$directory" fetch --depth 1 origin "$revision"
  git -C "$directory" checkout --detach "$revision"
  test "$(git -C "$directory" rev-parse HEAD)" = "$revision"
}
link_tool() {
  if test -L "$2" && test "$(readlink "$2")" = "$1"; then return; fi
  if test -e "$2" || test -L "$2"; then
    echo "Unexpected existing tool path: $2" >&2
    exit 1
  fi
  ln -s "$1" "$2"
}
[[ "${BASH_SOURCE[0]}" == "$0" ]] || return 0
cd "$(dirname "$0")/.."
root="$PWD"
test "$(uname -sm)" = 'Linux x86_64' || { echo 'Toolchain requires Linux x86_64' >&2; exit 1; }
for tool in curl git cmake make gcc g++ pkg-config unzip; do
  command -v "$tool" >/dev/null || { echo "Missing build dependency: $tool" >&2; exit 1; }
done
mkdir -p .runtime/bin
jobs="${BUILD_JOBS:-4}"
# uv manages only this project's environment; no global packages are changed.
download .runtime/uv-0.12.23.tar.gz \
  9167d72b3319674b6303c4cbe071854bba13ebdf3d76b1a7cbdc175471fb66d6 \
  https://github.com/astral-sh/uv/releases/download/0.12.23/uv-x86_64-unknown-linux-gnu.tar.gz
tar xzf .runtime/uv-0.12.23.tar.gz -C .runtime
install -m755 .runtime/uv-x86_64-unknown-linux-gnu/uv .runtime/bin/uv
python_runtime="${PYTHON3:-3.14.8}"
if test "$python_runtime" = 3.14.8 && command -v mise >/dev/null; then
  mise_python="$(mise where python@3.14.8 2>/dev/null || true)"
  if test -x "$mise_python/bin/python3"; then python_runtime="$mise_python/bin/python3"; fi
fi
.runtime/bin/uv sync --locked --python "$python_runtime"
.venv/bin/python -c 'import sys; assert sys.version_info[:3] == (3, 14, 8), sys.version'

# A completed stamp is bound to this installer, including all version pins.
installer_digest="$(sha256sum extra/setup_fork_tests.sh | cut -d' ' -f1)"
if test -f .runtime/toolchain.ready && test "$(cat .runtime/toolchain.ready)" = "$installer_digest"; then
  echo 'Pinned native toolchain already built.'
  exit 0
fi

download .runtime/oxipng.tar.gz \
  1813750ef592c5350ca79c88f98b2c0876d05c826dc7156245256d4255c1ad17 \
  https://github.com/oxipng/oxipng/releases/download/v10.2.1/oxipng-10.2.1-x86_64-unknown-linux-musl.tar.gz
tar xzf .runtime/oxipng.tar.gz -C .runtime
install -m755 .runtime/oxipng-10.2.1-x86_64-unknown-linux-musl/oxipng .runtime/bin/oxipng
checkout .runtime/jbig2enc-src https://github.com/agl/jbig2enc.git \
  309b2d55c7dfdcf0ab6afccb6d88834afc0bf2c0
cmake -S .runtime/jbig2enc-src -B .runtime/jbig2enc-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$root/.runtime/modern"
cmake --build .runtime/jbig2enc-build -j"$jobs"
cmake --install .runtime/jbig2enc-build
install -m755 .runtime/modern/bin/jbig2 .runtime/bin/jbig2

download .runtime/ghostscript-10.08.0.tar.xz \
  c20492bc8ebb96c87fa2e52a0926e1cda8cde95d66145e018ac713fed5da38cf \
  https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10080/ghostscript-10.08.0.tar.xz
if ! test -d .runtime/ghostscript-10.08.0; then
  tar xf .runtime/ghostscript-10.08.0.tar.xz -C .runtime
fi
(
  cd .runtime/ghostscript-10.08.0
  ./configure --prefix="$root/.runtime/ghostscript" --without-x --disable-cups --disable-gtk --without-tesseract
  make -j"$jobs"
  make install
) > .runtime/ghostscript-build.log 2>&1
link_tool ../ghostscript/bin/gs .runtime/bin/gs

download .runtime/qpdf-12.4.2.zip \
  db367d897829f22c4198ce1094143c9d467bd6ee7dfabc44ba6f02056b24f8b1 \
  https://github.com/qpdf/qpdf/releases/download/v12.4.2/qpdf-12.4.2-bin-linux-x86_64.zip
if ! test -d .runtime/qpdf12; then unzip -q .runtime/qpdf-12.4.2.zip -d .runtime/qpdf12; fi
link_tool ../qpdf12/bin/qpdf .runtime/bin/qpdf

download .runtime/poppler-26.10.0.tar.xz \
  6792cb7c69205007ad87d2e936cecc5b3a31fac29ab54ffc3175fdb6b2a6ce35 \
  https://poppler.freedesktop.org/poppler-26.10.0.tar.xz
if ! test -d .runtime/poppler-26.10.0; then tar xf .runtime/poppler-26.10.0.tar.xz -C .runtime; fi
cmake -S .runtime/poppler-26.10.0 -B .runtime/poppler-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$root/.runtime/modern" \
  '-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib' \
  -DENABLE_GLIB=OFF -DENABLE_GOBJECT_INTROSPECTION=OFF -DENABLE_QT5=OFF \
  -DENABLE_QT6=OFF -DENABLE_CPP=OFF -DENABLE_BOOST=OFF -DENABLE_LIBCURL=OFF \
  -DENABLE_GPGME=OFF -DENABLE_NSS3=OFF -DENABLE_GTK_DOC=OFF \
  -DBUILD_GTK_TESTS=OFF -DBUILD_QT5_TESTS=OFF -DBUILD_QT6_TESTS=OFF \
  -DBUILD_CPP_TESTS=OFF -DBUILD_MANUAL_TESTS=OFF
cmake --build .runtime/poppler-build -j"$jobs"
cmake --install .runtime/poppler-build
for tool in pdftoppm pdffonts pdftotext; do link_tool "../modern/bin/$tool" ".runtime/bin/$tool"; done
.runtime/bin/gs --version
.runtime/bin/qpdf --version
.runtime/bin/pdftoppm -v
printf '%s\n' "$installer_digest" > .runtime/toolchain.ready
