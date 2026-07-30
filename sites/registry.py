from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REGISTRY_FORMAT = "njupt-site-registry-v1"


@dataclass(frozen=True)
class SiteRegistration:
    id: str
    config: str
    plugin: str | None


def load_site_registry(
    path: Path,
    include: str | None = None,
) -> list[SiteRegistration]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"version", "sites"}:
        raise ValueError(f"{path} must contain exactly version and sites")
    if payload["version"] != REGISTRY_FORMAT:
        raise ValueError(f"{path} has an unsupported version")
    raw_sites = payload["sites"]
    if not isinstance(raw_sites, list) or not raw_sites:
        raise ValueError(f"{path} must contain sites")

    sites: list[SiteRegistration] = []
    seen: set[str] = set()
    for raw in raw_sites:
        if not isinstance(raw, dict) or not set(raw).issubset({"id", "config", "plugin"}):
            raise ValueError(f"invalid registry entry: {raw!r}")
        site_id = raw.get("id")
        config = raw.get("config")
        plugin = raw.get("plugin")
        if (
            not isinstance(site_id, str)
            or not site_id.strip()
            or not isinstance(config, str)
            or not config.strip()
            or (plugin is not None and (not isinstance(plugin, str) or not plugin.strip()))
        ):
            raise ValueError(f"invalid registry entry: {raw!r}")
        site_id = site_id.strip()
        if site_id in seen:
            raise ValueError(f"duplicate site id: {site_id}")
        seen.add(site_id)
        sites.append(
            SiteRegistration(
                id=site_id,
                config=config.strip(),
                plugin=plugin.strip() if plugin else None,
            )
        )

    if not include:
        return sites
    requested = {item.strip() for item in include.split(",") if item.strip()}
    selected = [site for site in sites if site.id in requested]
    missing = requested - {site.id for site in selected}
    if missing:
        raise ValueError(f"unknown site ids: {', '.join(sorted(missing))}")
    return selected
