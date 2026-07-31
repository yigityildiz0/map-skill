#!/usr/bin/env python3
"""Build deterministic standalone skills and the all-in-one Map Skill plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
PROFILES_PATH = ROOT / "city-editions" / "city-profiles.json"
UNIVERSAL = ROOT / "skills" / "plan-smart-routes"
ISTANBUL = ROOT / "skills" / "plan-smart-routes-istanbul"
REPO_PLUGIN = ROOT / "plugins" / "map-skill"
ZIP_TIME = (2026, 7, 31, 0, 0, 0)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_remove(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != ROOT.resolve() or resolved.name not in {"dist", "build"}:
        raise RuntimeError(f"Refusing to remove unexpected path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def is_link_like(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def assert_no_links(source: Path) -> None:
    for path in source.rglob("*"):
        if is_link_like(path):
            raise RuntimeError(f"Refusing to package symlink/junction: {path}")


def copy_tree(source: Path, target: Path) -> None:
    assert_no_links(source)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"),
    )


def replace_frontmatter(text: str, name: str, description: str) -> str:
    match = re.match(r"\A---\n.*?\n---\n", text, flags=re.DOTALL)
    if not match:
        raise RuntimeError("SKILL.md has no valid frontmatter")
    frontmatter = f"---\nname: {name}\ndescription: {description}\n---\n"
    return frontmatter + text[match.end() :]


def make_city_skill(profile: dict[str, Any], target: Path) -> None:
    slug = str(profile["slug"])
    if slug == "istanbul":
        copy_tree(ISTANBUL, target)
        return

    copy_tree(UNIVERSAL, target)
    city = str(profile["name"])
    local = str(profile.get("local_name") or city)
    skill_name = str(profile["release_skill"])
    description = (
        f"Plan and compare reliable {city} trips with public transport plus walking by default, "
        "official local transit and traffic checks, weather, opening hours, fares, multi-stop "
        "scheduling, ETA uncertainty, and valid navigation links. Use for any route, ETA, "
        f"arrival/departure, or multi-stop request whose origin, destination, or leg is in {city}."
    )
    skill_path = target / "SKILL.md"
    text = replace_frontmatter(skill_path.read_text(encoding="utf-8"), skill_name, description)
    text = text.replace("# Plan Smart Routes — Universal", f"# Plan Smart Routes — {city}", 1)
    marker = f"# Plan Smart Routes — {city}\n"
    city_note = (
        "\n## City Edition\n\n"
        f"This edition specializes the universal workflow for **{city} ({local})**. "
        "Read `references/city-profile.json` for every in-scope trip. Use only sources whose "
        "access requirements are satisfied, preserve their coverage gaps, and fall back to the "
        "universal source plan outside the documented area.\n"
    )
    text = text.replace(marker, marker + city_note, 1)
    skill_path.write_text(text, encoding="utf-8", newline="\n")
    (target / "references" / "city-profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    display = f"Map Skill — {local}"
    yaml_text = (
        "interface:\n"
        f"  display_name: {json.dumps(display, ensure_ascii=False)}\n"
        f"  short_description: {json.dumps('Official-source route planning for ' + city, ensure_ascii=False)}\n"
        f"  default_prompt: {json.dumps('Use $' + skill_name + ' to plan my trip with current official checks and truthful map links.', ensure_ascii=False)}\n"
    )
    (target / "agents" / "openai.yaml").write_text(yaml_text, encoding="utf-8", newline="\n")


def add_to_zip(archive: zipfile.ZipFile, source: Path, arc_root: str) -> None:
    assert_no_links(source)
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        relative = path.relative_to(source).as_posix()
        info = zipfile.ZipInfo(f"{arc_root}/{relative}", ZIP_TIME)
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        mode = stat.S_IFREG | (0o755 if path.suffix in {".py", ".sh"} else 0o644)
        info.external_attr = mode << 16
        archive.writestr(info, path.read_bytes())


def zip_tree(source: Path, destination: Path, arc_root: str) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        add_to_zip(archive, source, arc_root)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="Remove existing build/dist directories first")
    args = parser.parse_args()

    if args.clean:
        safe_remove(BUILD)
        safe_remove(DIST)
    BUILD.mkdir(exist_ok=True)
    DIST.mkdir(exist_ok=True)

    manifest = load_json(ROOT / ".codex-plugin" / "plugin.json")
    version = str(manifest["version"])
    registry = load_json(PROFILES_PATH)
    profiles = registry["profiles"]

    # Keep the universal skill's bundled registry synchronized with the canonical source file.
    registry_target = UNIVERSAL / "references" / "city-source-registry.json"
    shutil.copy2(PROFILES_PATH, registry_target)

    city_build = BUILD / "city-skills"
    city_build.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[dict[str, Any], Path]] = []
    for profile in profiles:
        target = city_build / str(profile["release_skill"])
        make_city_skill(profile, target)
        generated.append((profile, target))

    # Materialize the Git-backed marketplace plugin with Universal plus every
    # city edition so the GitHub marketplace install matches the release bundle.
    if REPO_PLUGIN.exists():
        shutil.rmtree(REPO_PLUGIN)
    REPO_PLUGIN.mkdir(parents=True)
    copy_tree(ROOT / ".codex-plugin", REPO_PLUGIN / ".codex-plugin")
    (REPO_PLUGIN / "skills").mkdir()
    copy_tree(UNIVERSAL, REPO_PLUGIN / "skills" / "plan-smart-routes")
    for profile, target in generated:
        copy_tree(target, REPO_PLUGIN / "skills" / target.name)
    shutil.copy2(ROOT / "LICENSE", REPO_PLUGIN / "LICENSE")

    assets: list[dict[str, Any]] = []

    def register(path: Path, kind: str, city: str | None = None) -> None:
        assets.append(
            {
                "file": path.name,
                "kind": kind,
                "city": city,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    universal_zip = DIST / "map-skill-universal.zip"
    zip_tree(UNIVERSAL, universal_zip, "plan-smart-routes")
    register(universal_zip, "standalone_skill", "Universal")

    for profile, target in generated:
        slug = str(profile["slug"])
        output = DIST / f"map-skill-{slug}.zip"
        zip_tree(target, output, target.name)
        register(output, "city_skill", str(profile["name"]))

    all_cities_zip = DIST / "map-skill-city-editions.zip"
    zip_tree(city_build, all_cities_zip, "map-skill-city-editions")
    register(all_cities_zip, "city_bundle", "All city editions")

    plugin_stage = BUILD / "map-skill"
    plugin_stage.mkdir(parents=True, exist_ok=True)
    copy_tree(ROOT / ".codex-plugin", plugin_stage / ".codex-plugin")
    (plugin_stage / "skills").mkdir()
    copy_tree(UNIVERSAL, plugin_stage / "skills" / "plan-smart-routes")
    for profile, target in generated:
        copy_tree(target, plugin_stage / "skills" / target.name)
    shutil.copy2(ROOT / "LICENSE", plugin_stage / "LICENSE")
    shutil.copy2(ROOT / "README.md", plugin_stage / "README.md")
    copy_tree(ROOT / "docs", plugin_stage / "docs")
    (plugin_stage / "city-editions").mkdir()
    shutil.copy2(PROFILES_PATH, plugin_stage / "city-editions" / "city-profiles.json")
    plugin_zip = DIST / "map-skill-plugin.zip"
    zip_tree(plugin_stage, plugin_zip, "map-skill")
    register(plugin_zip, "plugin", "Universal plus all city editions")

    release_manifest = {
        "project": "map-skill",
        "version": version,
        "built_on": "2026-07-31",
        "profile_registry_verified_on": registry.get("verified_on"),
        "city_count": len(profiles),
        "assets": sorted(assets, key=lambda item: item["file"]),
    }
    manifest_path = DIST / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sums = [f"{item['sha256']}  {item['file']}" for item in release_manifest["assets"]]
    sums.append(f"{sha256(manifest_path)}  {manifest_path.name}")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    print(f"Built {len(assets)} archives for {len(profiles)} city profiles in {DIST}")


if __name__ == "__main__":
    main()
