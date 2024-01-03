#/bin/bash

# Prerequesites
sudo python3 -m pip install -U build cibuildwheel PyYAML requests
sudo apt install -y jq wget curl

# Variables
export PKGNAME="borgbackup"
export PKGVER=$(grep "${PKGNAME}" requirements.txt | cut -d '=' -f 3 | tr -d '\012\015')
export PKGURL=$(curl -s "https://pypi.org/pypi/${PKGNAME}/${PKGVER}/json" | jq -r '.urls[].url')
export CIBW_BEFORE_ALL='apk add -Uu acl-dev alpine-sdk attr-dev attr-dev bzip2-dev fuse-dev g++ libcrypto1.1 libffi-dev libssl1.1 libxxhash linux-headers lz4-dev musl-dev ncurses-dev openssl-dev py3-msgpack py3-packaging py3-pip py3-setuptools py3-setuptools_scm py3-wheel py3-xxhash python3-dev readline-dev sqlite-dev tree xxhash-dev xz-dev zlib-dev zstd-dev && pip install -U pkgconfig pip setuptools wheel'
export CIBW_ARCHS_LINUX='x86_64 aarch64'
export CIBW_BUILD='cp311-musllinux_*'

# Load Multiarch settings
docker run --rm --privileged tonistiigi/binfmt
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Create directories
mkdir -p sdist wheelhouse

# Download
wget -c $PKGURL -q -O - | tar -xz -C ./sdist/

# Build
cibuildwheel --platform linux --output-dir wheelhouse sdist/$PKGNAME-$PKGVER

# Remove working files
rm -rf ./sdist/$PKGNAME*

# Remove leftover Docker images
docker inspect --type=image tonistiigi/binfmt >/dev/null 2>&1 && docker rmi tonistiigi/binfmt || echo 'binfmt image does not exist. Will not delete.'
docker inspect --type=image quay.io/pypa/musllinux_1_1_x86_64 >/dev/null 2>&1 && docker rmi multiarch/qemu-user-static || echo 'qemu-user-static image does not exist. Will not delete.'
docker images | grep quay.io/pypa/ | awk "{print \$3}" >/dev/null 2>&1 && docker rmi $(docker images | grep quay.io/pypa/ | awk "{print \$3}") || echo 'quay.io/pypa image does not exist. Will not delete.'

