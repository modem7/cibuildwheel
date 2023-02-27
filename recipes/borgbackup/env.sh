export CIBW_BEFORE_ALL='apk add -Uu acl-dev alpine-sdk attr-dev attr-dev bzip2-dev fuse-dev g++ libcrypto1.1 libffi-dev libssl1.1 libxxhash linux-headers lz4-dev musl-dev ncurses-dev openssl-dev py3-msgpack py3-packaging py3-pip py3-setuptools py3-setuptools_scm py3-wheel py3-xxhash python3-dev readline-dev sqlite-dev tree xxhash-dev xz-dev zlib-dev zstd-dev && pip install -U pkgconfig pip setuptools wheel'
export CIBW_ARCHS_LINUX='x86_64 aarch64'
