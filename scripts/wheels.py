#!/usr/bin/env python3
"""Plan and build the wheels described by build.yaml and recipes/*/recipe.yaml.

wheels.py plan                      list wheels missing from the index
wheels.py build <recipe>            build a recipe with cibuildwheel
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent.parent
RECIPE_KEYS = {"name", "version", "version_from", "apk", "environment", "test"}
# GitHub-hosted runner that builds each arch natively.
RUNNERS = {"x86_64": "ubuntu-24.04", "aarch64": "ubuntu-24.04-arm"}


def load_config(root=ROOT):
    with open(root / "build.yaml") as f:
        config = yaml.safe_load(f)
    for version in config["python"]:
        if not isinstance(version, str) or not re.fullmatch(r"3\.\d+", version):
            raise SystemExit(f'build.yaml: python version {version!r} must be a quoted string like "3.14"')
    for arch in config["archs"]:
        if arch not in RUNNERS:
            raise SystemExit(f"build.yaml: unknown arch {arch!r} (known: {', '.join(RUNNERS)})")
    return config


def load_recipe(path):
    with open(path) as f:
        recipe = yaml.safe_load(f)
    unknown = set(recipe) - RECIPE_KEYS
    if unknown:
        raise SystemExit(f"{path}: unknown keys: {', '.join(sorted(unknown))}")
    if not isinstance(recipe.get("name"), str):
        raise SystemExit(f"{path}: 'name' is required and must be a string")
    if ("version" in recipe) == ("version_from" in recipe):
        raise SystemExit(f"{path}: set exactly one of 'version' and 'version_from'")
    for key in ("version", "version_from"):
        if key in recipe and not isinstance(recipe[key], str):
            raise SystemExit(f"{path}: {key!r} must be a string (quote the version)")
    recipe.setdefault("apk", [])
    recipe.setdefault("environment", {})
    recipe.setdefault("test", None)
    return recipe


def load_recipes(root=ROOT):
    return {path.parent.name: load_recipe(path) for path in sorted(root.glob("recipes/*/recipe.yaml"))}


def pypi_json(path):
    with urllib.request.urlopen(f"https://pypi.org/pypi/{path}/json", timeout=30) as response:
        return json.load(response)


def newest_allowed(name, requires_dist, releases):
    """Return the newest of releases that the requirement on name in requires_dist allows."""
    for line in requires_dist or []:
        requirement = Requirement(line)
        if canonicalize_name(requirement.name) != canonicalize_name(name):
            continue
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        allowed = list(requirement.specifier.filter(releases))
        if not allowed:
            raise SystemExit(f"No release of {name} satisfies {line!r}")
        return str(max(allowed, key=Version))
    raise SystemExit(f"No requirement on {name} found")


def resolve_versions(recipes, fetch=pypi_json):
    """Fill in the version of every recipe that takes it from another recipe's requirement."""
    for recipe_dir, recipe in recipes.items():
        source_dir = recipe.get("version_from")
        if source_dir is None:
            continue
        source = recipes.get(source_dir)
        if source is None or "version" not in source:
            raise SystemExit(f"recipes/{recipe_dir}: version_from must name a recipe with a fixed version")
        requires_dist = fetch(f"{source['name']}/{source['version']}")["info"]["requires_dist"]
        releases = [
            version
            for version, files in fetch(recipe["name"])["releases"].items()
            if is_version(version) and any(f["packagetype"] == "sdist" and not f["yanked"] for f in files)
        ]
        recipe["version"] = newest_allowed(recipe["name"], requires_dist, releases)
    return recipes


def is_version(text):
    try:
        Version(text)
    except InvalidVersion:
        return False
    return True


def cp_tag(python_version):
    return "cp" + python_version.replace(".", "")


def published_wheels(index_url, name):
    """Return the wheel filenames the index lists for a package."""
    url = f"{index_url.rstrip('/')}/{canonicalize_name(name)}/"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            html = response.read().decode()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    return sorted(set(re.findall(r">\s*([^<>\s]+\.whl)\s*<", html)))


def is_published(recipe, python_version, arch, filenames):
    """Whether a musllinux wheel for this recipe version, Python and arch is among filenames."""
    for filename in filenames:
        name, version, _, tags = parse_wheel_filename(filename)
        if name != canonicalize_name(recipe["name"]) or version != Version(recipe["version"]):
            continue
        for tag in tags:
            if (
                tag.interpreter == tag.abi == cp_tag(python_version)
                and tag.platform.startswith("musllinux_")
                and tag.platform.endswith(f"_{arch}")
            ):
                return True
    return False


def plan(config, recipes, published, force=False):
    """Return one build job per recipe and arch that has Python versions left to build.

    published maps recipe directory name to the wheel filenames already on the index.
    """
    jobs = []
    for recipe_dir, recipe in recipes.items():
        for arch in config["archs"]:
            pythons = [
                version
                for version in config["python"]
                if force or not is_published(recipe, version, arch, published.get(recipe_dir, []))
            ]
            if pythons:
                jobs.append(
                    {
                        "recipe": recipe_dir,
                        "version": recipe["version"],
                        "arch": arch,
                        "python": " ".join(pythons),
                        "runner": RUNNERS[arch],
                    }
                )
    return jobs


def cibuildwheel_env(recipe, python_versions, archs):
    env = {
        "CIBW_BUILD": " ".join(f"{cp_tag(version)}-musllinux_*" for version in python_versions),
        "CIBW_ARCHS_LINUX": " ".join(archs),
    }
    if recipe["apk"]:
        env["CIBW_BEFORE_ALL_LINUX"] = "apk add --no-cache " + " ".join(recipe["apk"])
    if recipe["environment"]:
        env["CIBW_ENVIRONMENT"] = " ".join(f'{key}="{value}"' for key, value in recipe["environment"].items())
    if recipe["test"]:
        env["CIBW_TEST_COMMAND"] = recipe["test"]
    return env


def download_sdist(recipe, dest_dir):
    """Download the recipe's sdist from PyPI, verify its checksum and return its path."""
    url = f"https://pypi.org/pypi/{recipe['name']}/{recipe['version']}/json"
    files = pypi_json(f"{recipe['name']}/{recipe['version']}")["urls"]
    sdists = [file for file in files if file["packagetype"] == "sdist"]
    if len(sdists) != 1:
        raise SystemExit(f"Expected exactly one sdist at {url}, found {len(sdists)}")
    sdist = sdists[0]
    path = Path(dest_dir) / sdist["filename"]
    print(f"Downloading {sdist['url']}", flush=True)
    with urllib.request.urlopen(sdist["url"], timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != sdist["digests"]["sha256"]:
        raise SystemExit(f"Checksum mismatch for {sdist['filename']}")
    path.write_bytes(data)
    return path


def cmd_plan(args):
    config = load_config()
    recipes = resolve_versions(load_recipes())
    published = {} if args.force else {d: published_wheels(config["index_url"], r["name"]) for d, r in recipes.items()}
    jobs = plan(config, recipes, published, force=args.force)
    for job in jobs:
        print(f"{job['recipe']} {job['version']} {job['arch']}: python {job['python']}")
    if not jobs:
        print("Nothing to build: every wheel is already on the index.")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"matrix={json.dumps({'include': jobs})}\n")
            f.write(f"has_work={'true' if jobs else 'false'}\n")
            f.write(f"cloudsmith_repo={config['cloudsmith_repo']}\n")


def cmd_build(args):
    config = load_config()
    recipes = resolve_versions(load_recipes())
    if args.recipe not in recipes:
        raise SystemExit(f"Unknown recipe {args.recipe!r} (available: {', '.join(recipes)})")
    recipe = recipes[args.recipe]
    env = cibuildwheel_env(recipe, args.python or config["python"], args.arch or config["archs"])
    for key, value in env.items():
        print(f"{key}={value}")
    with tempfile.TemporaryDirectory() as temp_dir:
        sdist = download_sdist(recipe, temp_dir)
        command = ["cibuildwheel", "--platform", "linux", "--output-dir", args.output_dir, str(sdist)]
        subprocess.run(command, env={**os.environ, **env}, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="list the wheels missing from the index")
    plan_parser.add_argument("--force", action="store_true", help="plan every wheel, published or not")
    plan_parser.add_argument("--github-output", action="store_true", help="write the job matrix to $GITHUB_OUTPUT")
    plan_parser.set_defaults(func=cmd_plan)

    build_parser = subparsers.add_parser("build", help="build a recipe with cibuildwheel")
    build_parser.add_argument("recipe", help="directory name under recipes/")
    build_parser.add_argument("--python", nargs="+", metavar="X.Y", help="default: all versions in build.yaml")
    build_parser.add_argument("--arch", nargs="+", choices=sorted(RUNNERS), help="default: all archs in build.yaml")
    build_parser.add_argument("--output-dir", default="wheelhouse")
    build_parser.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
