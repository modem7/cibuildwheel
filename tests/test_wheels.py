import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest  # noqa: E402
import wheels  # noqa: E402

CONFIG = {"python": ["3.14", "3.15"], "archs": ["x86_64", "aarch64"]}
BORG = {"name": "borgbackup", "version": "1.4.5", "apk": ["openssl-dev"], "environment": {}, "test": "borg --version"}
CLIB = {"name": "ruamel.yaml.clib", "version": "0.2.15", "apk": [], "environment": {}, "test": None}


def test_is_published_matches_python_arch_and_version():
    filenames = ["borgbackup-1.4.5-cp314-cp314-musllinux_1_2_x86_64.whl"]
    assert wheels.is_published(BORG, "3.14", "x86_64", filenames)
    assert not wheels.is_published(BORG, "3.15", "x86_64", filenames)
    assert not wheels.is_published(BORG, "3.14", "aarch64", filenames)
    assert not wheels.is_published({**BORG, "version": "1.4.6"}, "3.14", "x86_64", filenames)


def test_is_published_ignores_manylinux_and_normalises_names():
    assert not wheels.is_published(BORG, "3.14", "x86_64", ["borgbackup-1.4.5-cp314-cp314-manylinux_2_28_x86_64.whl"])
    for filename in (
        "ruamel.yaml.clib-0.2.15-cp314-cp314-musllinux_1_2_x86_64.whl",
        "ruamel_yaml_clib-0.2.15-cp314-cp314-musllinux_1_2_x86_64.whl",
    ):
        assert wheels.is_published(CLIB, "3.14", "x86_64", [filename])


def test_plan_only_lists_missing_wheels():
    published = {
        "borgbackup": [
            "borgbackup-1.4.5-cp314-cp314-musllinux_1_2_x86_64.whl",
            "borgbackup-1.4.5-cp314-cp314-musllinux_1_2_aarch64.whl",
            "borgbackup-1.4.5-cp315-cp315-musllinux_1_2_aarch64.whl",
        ]
    }
    assert wheels.plan(CONFIG, {"borgbackup": BORG}, published) == [
        {"recipe": "borgbackup", "version": "1.4.5", "arch": "x86_64", "python": "3.15", "runner": "ubuntu-24.04"}
    ]


def test_plan_builds_everything_for_unpublished_or_forced():
    everything = [("x86_64", "3.14 3.15"), ("aarch64", "3.14 3.15")]
    jobs = wheels.plan(CONFIG, {"borgbackup": BORG}, {})
    assert [(job["arch"], job["python"]) for job in jobs] == everything

    published = {
        "borgbackup": [
            f"borgbackup-1.4.5-{cp}-{cp}-musllinux_1_2_{arch}.whl"
            for cp in ("cp314", "cp315")
            for arch in CONFIG["archs"]
        ]
    }
    assert wheels.plan(CONFIG, {"borgbackup": BORG}, published) == []
    jobs = wheels.plan(CONFIG, {"borgbackup": BORG}, published, force=True)
    assert [(job["arch"], job["python"]) for job in jobs] == everything


def test_cibuildwheel_env():
    recipe = {**BORG, "environment": {"FOO": "bar baz"}}
    assert wheels.cibuildwheel_env(recipe, ["3.14", "3.15"], ["x86_64"]) == {
        "CIBW_BUILD": "cp314-musllinux_* cp315-musllinux_*",
        "CIBW_ARCHS_LINUX": "x86_64",
        "CIBW_BEFORE_ALL_LINUX": "apk add --no-cache openssl-dev",
        "CIBW_ENVIRONMENT": 'FOO="bar baz"',
        "CIBW_TEST_COMMAND": "borg --version",
    }
    assert wheels.cibuildwheel_env(CLIB, ["3.14"], ["aarch64"]) == {
        "CIBW_BUILD": "cp314-musllinux_*",
        "CIBW_ARCHS_LINUX": "aarch64",
    }


BORG_REQUIRES = ["msgpack<=1.2.1,>=1.0.3", "packaging", 'llfuse>=1.3.8; extra == "llfuse"']


def test_newest_allowed_picks_highest_release_within_requirement():
    releases = ["1.0.2", "1.0.3", "1.2.0", "1.2.1", "1.2.3", "1.3.0rc1"]
    assert wheels.newest_allowed("msgpack", BORG_REQUIRES, releases) == "1.2.1"
    assert wheels.newest_allowed("msgpack", ["msgpack>=1.0.3"], releases) == "1.2.3"


def test_newest_allowed_ignores_extras_and_reports_no_match():
    with pytest.raises(SystemExit):
        wheels.newest_allowed("llfuse", BORG_REQUIRES, ["1.5.2"])
    with pytest.raises(SystemExit):
        wheels.newest_allowed("msgpack", BORG_REQUIRES, ["1.2.3"])


def test_resolve_versions_follows_the_named_recipe():
    def fetch(path):
        if path == "borgbackup/1.4.5":
            return {"info": {"requires_dist": BORG_REQUIRES}}
        assert path == "msgpack"
        sdist = [{"packagetype": "sdist", "yanked": False}]
        return {
            "releases": {
                "1.2.0": sdist,
                "1.2.1": sdist,
                "1.2.1.post1": [{"packagetype": "sdist", "yanked": True}],
                "1.2.3": sdist,
                "not-a-version": sdist,
            }
        }

    recipes = {"borgbackup": dict(BORG), "msgpack": {"name": "msgpack", "version_from": "borgbackup"}}
    assert wheels.resolve_versions(recipes, fetch)["msgpack"]["version"] == "1.2.1"
    with pytest.raises(SystemExit):
        wheels.resolve_versions({"msgpack": {"name": "msgpack", "version_from": "borgbackup"}}, fetch)


def test_repo_config_and_recipes_load():
    config = wheels.load_config()
    recipes = wheels.load_recipes()
    assert config["python"] and config["archs"] and recipes
    for directory, recipe in recipes.items():
        assert wheels.canonicalize_name(recipe["name"]) == wheels.canonicalize_name(directory)
