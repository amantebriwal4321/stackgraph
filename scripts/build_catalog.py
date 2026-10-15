"""Build seed/catalog.json from the editorial list plus public registries.

Run from the repo root:

    python scripts/build_catalog.py

Network is required. The committed catalog is what the demo loads, so a later
offline start does not call the registries.
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seed.editorial import ALTERNATIVES, CATEGORIES, MAINTAINERS, SIGNALS, TOOLS  # noqa: E402

OUT = ROOT / "seed" / "catalog.json"
HEADERS = {"User-Agent": "stackgraph-seed/0.1 (public registry metadata)"}
SPEC_SPLIT = re.compile(r"[<>=!~\[]")


def _license(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("type") or ""
    text = str(value).strip().splitlines()[0].strip()
    if len(text) > 48:
        return ""
    return text


def _repo(value) -> str:
    if isinstance(value, dict):
        value = value.get("url") or ""
    text = str(value or "").strip()
    if text.startswith("git+"):
        text = text[4:]
    if text.endswith(".git"):
        text = text[:-4]
    return text


def fetch_npm(client: httpx.Client, package: str) -> dict:
    url = f"https://registry.npmjs.org/{package}/latest"
    response = client.get(url)
    response.raise_for_status()
    data = response.json()
    return {
        "version": data.get("version") or "",
        "summary": (data.get("description") or "").strip()[:280],
        "license": _license(data.get("license")),
        "repo": _repo(data.get("repository")),
        "dependencies": data.get("dependencies") or {},
        "peerDependencies": data.get("peerDependencies") or {},
    }


def _pypi_deps(requires) -> dict:
    deps = {}
    for raw in requires or []:
        if not raw or not str(raw).strip():
            continue
        if ";" in raw and "extra" in raw.split(";", 1)[1].lower():
            # Skip optional extras. They are not installed with the package.
            continue
        base = raw.split(";")[0].strip()
        name = SPEC_SPLIT.split(base, maxsplit=1)[0].strip()
        if not name:
            continue
        spec = base[len(name) :].strip()
        deps[name.lower()] = spec
    return deps


def fetch_pypi(client: httpx.Client, package: str) -> dict:
    response = client.get(f"https://pypi.org/pypi/{package}/json")
    response.raise_for_status()
    info = response.json().get("info") or {}
    urls = info.get("project_urls") or {}
    repo = urls.get("Source") or urls.get("Repository") or urls.get("Homepage") or info.get("home_page") or ""
    return {
        "version": info.get("version") or "",
        "summary": (info.get("summary") or "").strip()[:280],
        "license": _license(info.get("license_expression") or info.get("license")),
        "repo": _repo(repo),
        "dependencies": _pypi_deps(info.get("requires_dist")),
        "peerDependencies": {},
    }


def main() -> None:
    names = [tool["package"] for tool in TOOLS]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate package names in editorial list")
    alias_owner = {}
    for tool in TOOLS:
        alias_owner[tool["package"].lower()] = tool["package"]
        for alias in tool.get("aliases") or []:
            key = alias.lower()
            if key in alias_owner:
                raise SystemExit(f"alias {alias} collides with {alias_owner[key]}")
            alias_owner[key] = tool["package"]

    known = {tool["package"] for tool in TOOLS}
    fetched: dict[str, dict] = {}
    errors = []
    with httpx.Client(headers=HEADERS, timeout=40.0, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {}
            for tool in TOOLS:
                fn = fetch_npm if tool["ecosystem"] == "npm" else fetch_pypi
                futures[pool.submit(fn, client, tool["package"])] = tool
            for future in as_completed(futures):
                tool = futures[future]
                try:
                    fetched[tool["package"]] = future.result()
                except Exception as exc:  # noqa: BLE001 - report every registry miss
                    errors.append(f"{tool['ecosystem']}:{tool['package']}: {exc}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(f"{len(errors)} registry fetches failed")

    dependencies = []
    for tool in TOOLS:
        meta = fetched[tool["package"]]
        for kind, field in (("runtime", "dependencies"), ("peer", "peerDependencies")):
            for dep_name, spec in (meta.get(field) or {}).items():
                if dep_name not in known or dep_name == tool["package"]:
                    continue
                dependencies.append(
                    {
                        "from": tool["package"],
                        "to": dep_name,
                        "kind": kind,
                        "spec": str(spec),
                    }
                )

    by_name = {tool["package"]: tool for tool in TOOLS}
    for src, dst, _reason in ALTERNATIVES:
        if src not in by_name or dst not in by_name:
            raise SystemExit(f"alternative names are not in the corpus: {src} -> {dst}")
    for signal in SIGNALS:
        if signal["tool"] not in by_name:
            raise SystemExit(f"signal tool missing: {signal['tool']}")

    tools_out = []
    for tool in TOOLS:
        meta = fetched[tool["package"]]
        tools_out.append(
            {
                "id": f"{tool['ecosystem']}:{tool['package']}",
                "name": tool["package"],
                "ecosystem": tool["ecosystem"],
                "package": tool["package"],
                "summary": meta["summary"],
                "license": meta["license"],
                "repo": meta["repo"],
                "version": meta["version"],
                "maintainer": tool["maintainer"],
                "categories": tool["categories"],
                "aliases": tool.get("aliases") or [],
                "legacy": bool(tool.get("legacy", False)),
                "origin": "public",
            }
        )

    catalog = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Descriptions, versions, licenses, repos, and dependency edges come from the public npm and PyPI registry documents fetched at generated_at. Alternative edges and the Moment signal are editorial. Scores on the seed signal are flags, not measurements.",
        "categories": CATEGORIES,
        "maintainers": MAINTAINERS,
        "tools": tools_out,
        "dependencies": dependencies,
        "alternatives": [
            {"from": src, "to": dst, "reason": reason} for src, dst, reason in ALTERNATIVES
        ],
        "signals": SIGNALS,
    }
    OUT.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"tools {len(tools_out)} dependency_edges {len(dependencies)} alternatives {len(ALTERNATIVES)}")
    for edge in dependencies:
        print(f"  {edge['from']} -{edge['kind']}-> {edge['to']} ({edge['spec']})")


if __name__ == "__main__":
    main()
