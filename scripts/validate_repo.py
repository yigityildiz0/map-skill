#!/usr/bin/env python3
"""Validate Map Skill source, profiles, scripts, links, and release checksums."""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ACCESS = {"no_key", "registration", "api_key", "web_only", "self_hosted", "unavailable"}
REQUIRED_CITIES = {
    "istanbul", "london", "paris", "berlin", "dublin", "milan", "madrid", "tokyo",
    "seoul", "singapore", "hong-kong", "toronto", "new-york", "chicago", "mexico-city", "sydney",
}
REQUIRED_TIMEZONES = {
    "Europe/Istanbul", "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Dublin", "Europe/Rome",
    "Europe/Madrid", "Asia/Tokyo", "Asia/Seoul", "Asia/Singapore", "Asia/Hong_Kong", "America/Toronto",
    "America/New_York", "America/Chicago", "America/Mexico_City", "Australia/Sydney",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def is_link_like(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        require(not is_link_like(item), f"symlink/junction is not allowed: {item}")
        if not item.is_file() or item.name in {"Thumbs.db", ".DS_Store"} or "__pycache__" in item.parts:
            continue
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256(item)))
    return digest.hexdigest().upper()


def validate_manifest() -> None:
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    require(manifest.get("name") == "map-skill", "plugin name must be map-skill")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version")))), "invalid semver")
    require(manifest.get("skills") == "./skills/", "plugin skills path must be ./skills/")
    require(manifest.get("author", {}).get("name"), "plugin author.name is required")
    require(manifest.get("interface", {}).get("displayName"), "plugin interface.displayName is required")
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    require(marketplace.get("name") == "map-skill", "marketplace name mismatch")
    entry = marketplace.get("plugins", [None])[0]
    require(entry and entry.get("source", {}).get("path") == "./plugins/map-skill", "marketplace source path mismatch")
    repo_plugin = ROOT / "plugins" / "map-skill"
    if repo_plugin.exists():
        nested = json.loads((repo_plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        require(nested.get("name") == "map-skill", "nested marketplace plugin mismatch")
        require((repo_plugin / "skills" / "plan-smart-routes" / "SKILL.md").exists(), "nested universal skill missing")
        require((repo_plugin / "skills" / "plan-smart-routes-istanbul" / "SKILL.md").exists(), "nested Istanbul skill missing")
        registry = json.loads((ROOT / "city-editions" / "city-profiles.json").read_text(encoding="utf-8"))
        expected_skills = {"plan-smart-routes"} | {str(item["release_skill"]) for item in registry["profiles"]}
        actual_skills = {item.name for item in (repo_plugin / "skills").iterdir() if item.is_dir()}
        require(actual_skills == expected_skills, f"nested plugin skill set mismatch: {actual_skills ^ expected_skills}")
        require(tree_digest(ROOT / ".codex-plugin") == tree_digest(repo_plugin / ".codex-plugin"), "nested manifest is stale")
        require(tree_digest(ROOT / "skills" / "plan-smart-routes") == tree_digest(repo_plugin / "skills" / "plan-smart-routes"), "nested universal skill is stale")
        require(tree_digest(ROOT / "skills" / "plan-smart-routes-istanbul") == tree_digest(repo_plugin / "skills" / "plan-smart-routes-istanbul"), "nested Istanbul skill is stale")
        require(sha256(ROOT / "LICENSE") == sha256(repo_plugin / "LICENSE"), "nested plugin licence is stale")
        generated = ROOT / "build" / "city-skills"
        if generated.exists():
            for skill_name in sorted(expected_skills - {"plan-smart-routes"}):
                require(
                    tree_digest(generated / skill_name) == tree_digest(repo_plugin / "skills" / skill_name),
                    f"nested generated skill is stale: {skill_name}",
                )


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    require(match is not None, f"missing frontmatter: {path}")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        require(bool(separator), f"invalid frontmatter line in {path}: {line}")
        fields[key.strip()] = value.strip()
    require(set(fields) == {"name", "description"}, f"only name/description allowed in {path}")
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"])), f"invalid skill name in {path}")
    require(len(fields["description"]) <= 1024, f"description too long in {path}")
    require("[TODO" not in text and "TODO:" not in text, f"placeholder remains in {path}")
    return fields


def validate_markdown_links(skill_dir: Path) -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for markdown in skill_dir.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for target in pattern.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            require((markdown.parent / clean).resolve().exists(), f"broken local link {target} in {markdown}")


def validate_repo_markdown_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for markdown in ROOT.rglob("*.md"):
        if any(part in {"build", "dist", ".git"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for target in pattern.findall(text):
            clean = target.split("#", 1)[0].strip("<>")
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            require((markdown.parent / clean).resolve().exists(), f"broken repository link {target} in {markdown}")


def validate_skills() -> None:
    names: set[str] = set()
    for skill_dir in sorted((ROOT / "skills").iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
            continue
        fields = parse_frontmatter(skill_dir / "SKILL.md")
        require(fields["name"] not in names, f"duplicate skill name: {fields['name']}")
        names.add(fields["name"])
        validate_markdown_links(skill_dir)
        for script in skill_dir.rglob("*.py"):
            with tempfile.TemporaryDirectory() as temp:
                py_compile.compile(str(script), cfile=str(Path(temp) / "compiled.pyc"), doraise=True)


def validate_profiles() -> None:
    registry = json.loads((ROOT / "city-editions" / "city-profiles.json").read_text(encoding="utf-8"))
    require(registry.get("verified_on") == "2026-07-31", "registry verification date mismatch")
    profiles = registry.get("profiles")
    require(isinstance(profiles, list), "profiles must be a list")
    slugs = [str(profile.get("slug")) for profile in profiles]
    require(set(slugs) == REQUIRED_CITIES, f"city set mismatch: {set(slugs) ^ REQUIRED_CITIES}")
    require(len(slugs) == len(set(slugs)), "duplicate city slug")
    skills: set[str] = set()
    for profile in profiles:
        skill = str(profile.get("release_skill"))
        require(skill and skill not in skills, f"duplicate/missing release skill: {skill}")
        skills.add(skill)
        require(str(profile.get("timezone")) in REQUIRED_TIMEZONES, f"invalid timezone for {profile.get('slug')}")
        sources = profile.get("sources")
        require(isinstance(sources, list) and sources, f"no sources for {profile.get('slug')}")
        for source in sources:
            require(source.get("access") in ALLOWED_ACCESS, f"invalid access type in {profile.get('slug')}")
            require(str(source.get("url", "")).startswith("https://"), f"non-HTTPS official URL in {profile.get('slug')}")
            require(source.get("kinds") and source.get("use") and source.get("limits"), f"incomplete source in {profile.get('slug')}")
            serialized = json.dumps(source).casefold()
            require("bearer " not in serialized, f"possible bearer credential in {profile.get('slug')}")
            require(not re.search(r"(?:ghp_|sk-)[a-z0-9_-]{16,}", serialized), f"possible credential in {profile.get('slug')}")


def run_json(command: list[str]) -> dict:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        command, cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8", env=environment
    )
    return json.loads(completed.stdout)


def validate_smoke() -> None:
    toolkit = ROOT / "skills" / "plan-smart-routes" / "scripts" / "route_toolkit.py"
    result = run_json(
        [
            sys.executable, str(toolkit), "--compact", "links",
            "--origin", "41.0082,28.9784|Origin",
            "--waypoint", "41.0256,28.9741|Stop",
            "--destination", "41.0422,29.0083|Destination",
            "--mode", "transit",
            "--when", "2026-08-01T09:00:00+03:00",
        ]
    )
    require(result.get("ok") is True, "link smoke failed")
    google = next(item for item in result["links"] if item["provider"] == "google")
    require(google["encodes"]["waypoints"] is True, "Google waypoint capability missing")
    require(google["encodes"]["time"] is False, "Google URL must not claim encoded time")
    require(result.get("integrity_note"), "link integrity note missing")

    registry = ROOT / "skills" / "plan-smart-routes" / "scripts" / "source_registry.py"
    profile = run_json([sys.executable, str(registry), "--compact", "show", "--city", "İstanbul"])
    require(profile.get("slug") == "istanbul", "registry matching failed")


def validate_zip_archive(archive: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        require(bool(infos), f"empty ZIP: {archive.name}")
        names: set[str] = set()
        folded_names: set[str] = set()
        roots: set[str] = set()
        total_size = 0
        for info in infos:
            name = info.filename
            require("\\" not in name, f"backslash ZIP path in {archive.name}: {name}")
            require(":" not in name, f"colon ZIP path in {archive.name}: {name}")
            path = PurePosixPath(name)
            require(not path.is_absolute(), f"absolute ZIP path in {archive.name}: {name}")
            require(path.as_posix() == name, f"non-normalized ZIP path in {archive.name}: {name}")
            require(".." not in path.parts and "." not in path.parts, f"traversal ZIP path in {archive.name}: {name}")
            require(name not in names and name.casefold() not in folded_names, f"duplicate ZIP member in {archive.name}: {name}")
            names.add(name)
            folded_names.add(name.casefold())
            require(bool(path.parts), f"empty ZIP member name in {archive.name}")
            roots.add(path.parts[0])
            require(info.create_system == 3, f"non-deterministic ZIP platform metadata in {archive.name}: {name}")
            unix_type = (info.external_attr >> 16) & 0o170000
            require(unix_type != stat.S_IFLNK, f"symlink ZIP member in {archive.name}: {name}")
            total_size += info.file_size
        require(len(roots) == 1, f"ZIP must have one top-level root in {archive.name}: {sorted(roots)}")
        require(total_size <= 100 * 1024 * 1024, f"ZIP expands beyond 100 MiB: {archive.name}")
        bad = handle.testzip()
        require(bad is None, f"corrupt ZIP member {bad} in {archive.name}")


def validate_dist() -> None:
    dist = ROOT / "dist"
    if not dist.exists():
        return
    sums = dist / "SHA256SUMS.txt"
    manifest = dist / "MANIFEST.json"
    require(sums.exists() and manifest.exists(), "dist checksums/manifest missing")
    for line in sums.read_text(encoding="utf-8").splitlines():
        expected, filename = line.split("  ", 1)
        path = dist / filename
        require(path.exists(), f"missing release asset: {filename}")
        require(sha256(path) == expected, f"checksum mismatch: {filename}")
    for archive in dist.glob("*.zip"):
        validate_zip_archive(archive)


def main() -> None:
    validate_manifest()
    validate_profiles()
    validate_skills()
    validate_repo_markdown_links()
    validate_smoke()
    validate_dist()
    print("VALIDATION_OK: plugin, 16 city profiles, skills, scripts, links, and distributions")


if __name__ == "__main__":
    main()
