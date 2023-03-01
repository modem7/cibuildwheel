export CIBW_BEFORE_ALL='apk add -Uu pkgconfig g++ yaml-dev python3-dev && pip install -U pkgconfig pip setuptools wheel'
export CIBW_ARCHS_LINUX='x86_64 aarch64'
export CIBW_ENVIRONMENT='C_INCLUDE_PATH=libyaml/include LIBRARY_PATH=libyaml/src/.libs LD_LIBRARY_PATH=libyaml/src/.libs PYYAML_FORCE_CYTHON=1 PYYAML_FORCE_LIBYAML=1'