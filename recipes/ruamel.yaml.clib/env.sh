export CIBW_BEFORE_ALL='apk add -Uu pkgconfig gcc musl-dev && pip install -U pkgconfig pip setuptools wheel'
export CIBW_ARCHS_LINUX='x86_64 aarch64'