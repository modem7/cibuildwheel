# CIBuildWheel repository.

[![GitHub last commit](https://img.shields.io/github/last-commit/modem7/cibuildwheel)](CIBuildWheel) [![Build and upload wheels](https://github.com/modem7/cibuildwheel/actions/workflows/ci.yaml/badge.svg)](https://github.com/modem7/cibuildwheel/actions/workflows/ci.yaml)

Recipes and continuous integration (CI) to build musllinux (Alpine) [wheels](https://pythonwheels.com/)
for Python packages that don't provide them on [PyPI](https://pypi.org/). Built with
[cibuildwheel](https://cibuildwheel.readthedocs.io) and hosted on
[Cloudsmith](https://dl.cloudsmith.io/public/modem7/wheels/python/simple/).

## Layout

| Path | Purpose |
| --- | --- |
| `build.yaml` | Python versions and architectures every recipe is built for |
| `recipes/<name>/recipe.yaml` | One package: version, system packages, build environment, test |
| `scripts/wheels.py` | Works out what is missing from the index and builds it |
| `.github/workflows/ci.yaml` | Runs the script and uploads the result |

## How it works

CI compares what should exist (every recipe × Python version × architecture) against the
Cloudsmith index and builds only what is missing. Pull requests build the missing wheels
as a check; pushes to `master` build and upload them. Nothing else triggers a build, so
every task below is a one-line change.

### Add or change a Python version

Edit the `python` list in `build.yaml`. Every recipe is built and uploaded for the new version.

### Update a package

Change `version` in its `recipe.yaml`. Renovate opens these PRs automatically.

### Follow another package's requirement

When one recipe limits which versions of another it accepts (borgbackup caps msgpack),
replace `version` with `version_from`:

```yaml
name: msgpack
version_from: borgbackup   # recipe directory name
```

The newest release that recipe's requirement allows is built, so it moves on its own
when the other package is updated. `wheels.py plan --force` shows the version chosen.

### Add a package

Create `recipes/<name>/recipe.yaml`, where `<name>` matches the PyPI name:

```yaml
---
name: borgbackup
version: "1.4.5"        # quoted; the sdist is downloaded from PyPI

apk:                    # Alpine packages the build needs, each with its reason
  - openssl-dev         # libcrypto

environment:            # optional: extra environment variables for the build
  SOME_FLAG: "1"

test: borg --version    # optional: run against each built wheel
```

### Rebuild everything

Run the workflow manually from the Actions tab with **force** ticked.

## Working out what a recipe needs

The `apk` list is the complete set of system packages for a build. The musllinux image
already ships gcc, g++, make, pkgconf and linux-headers, so list only the `-dev` packages
for libraries the package links against (see its `setup.py` or build documentation).

To check a list, build locally. A package is needed if removing its line makes the build
or the `test` command fail:

```bash
pip install -r scripts/requirements.txt
python scripts/wheels.py build borgbackup --python 3.15 --arch x86_64
```

This needs Docker. Wheels are written to `wheelhouse/`. Building an architecture other
than the host's also needs QEMU (`docker run --privileged --rm tonistiigi/binfmt --install all`).

To see what CI would build right now:

```bash
python scripts/wheels.py plan
```
