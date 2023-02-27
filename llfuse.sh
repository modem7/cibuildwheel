#/bin/bash

# Prerequesites
sudo python3 -m pip install -U build cibuildwheel PyYAML requests
sudo apt install -y jq wget curl

# Variables
export PKGNAME="llfuse"
export PKGVER=$(grep "${PKGNAME}" requirements.txt | cut -d '=' -f 3 | tr -d '\012\015')
export PKGURL=$(curl -s "https://pypi.org/pypi/${PKGNAME}/${PKGVER}/json" | jq -r '.urls[].url')
export CIBW_BEFORE_ALL='apk add -Uu pkgconfig fuse-dev g++ && pip install -U pkgconfig pip setuptools wheel'
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
docker rmi tonistiigi/binfmt
docker rmi multiarch/qemu-user-static
docker rmi $(docker images | grep quay.io/pypa/ | awk "{print \$3}")
