# CIBuildWheel repository.

[![GitHub last commit](https://img.shields.io/github/last-commit/modem7/cibuildwheel)](CIBuildWheel) [![Build and upload wheels](https://github.com/modem7/cibuildwheel/actions/workflows/ci.yaml/badge.svg)](https://github.com/modem7/cibuildwheel/actions/workflows/ci.yaml)

CIBuildWheel repository for [Modem7 Cloudsmith](https://dl.cloudsmith.io/public/modem7/wheels/python/simple/) Python packages. Built with [cibuildwheel](https://cibuildwheel.readthedocs.io) and hosted with [Cloudsmith](https://cloudsmith.io).

Recipes and continuous integration (CI) to build [wheels](https://pythonwheels.com/)
for Python packages that don't provide them on [PyPI](https://pypi.org/).

## Creating new packages

### Automatic

A package recipe is a simple `meta.yaml` file (in [YAML](https://yaml.org) format), contained in a
dedicated subdirectory of `recipes/` , specifying the package name and version,
e.g. the recipe for Mercurial 6.1.1 would be in the file `recipes/mercurial/meta.yaml`
containing:

```yaml
---
name: borgbackup
version: 1.2.3
```

When a recipe is added to this repository or updated (via PR), a CI job downloads from
PyPI the sdist archive for the specified package, and then builds the wheels
using either [cibuildwheel](https://cibuildwheel.readthedocs.io) (default) or
[build](https://pypa-build.readthedocs.io) (if it is a pure Python package
specified with `purepy: true` in the recipe).

### Manual

To build the wheels manually, run the manual scripts included in the repo.

Current scripts:
- borg.sh
- llfuse.sh
- msgpack.sh
- pyyaml.sh
- ruamel.yaml.clib.sh

The wheels will be output to the `wheelhouse` folder.

Once you have built the wheels, you can upload using the `cloudsmith.sh` script.

You can find your Cloudsmith API key [here](https://cloudsmith.io/user/settings/api/).