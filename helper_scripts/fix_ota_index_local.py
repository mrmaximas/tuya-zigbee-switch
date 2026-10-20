#!/usr/bin/env python3
"""Sync zigbee2mqtt OTA index entries with the locally built artifacts.

Only entries whose `url` points at a board directory that exists under
`bin/<type>/` are touched. Everything else is left alone, because the
index also lists firmware for the ~200 other devices in device_db.yaml
that were never built locally.

Rewrites fileSize and sha512 from the actual file on disk.
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def local_path_for(entry, device_type):
    m = re.search(r"/bin/([a-z_]+)/([A-Za-z0-9_]+)/([^/]+)$", entry["url"])
    if not m:
        return None
    _, board, filename = m.groups()
    p = os.path.join(ROOT, "bin", device_type, board, filename)
    return p if os.path.isfile(p) else None


def sync(index_file, device_type):
    path = os.path.join(ROOT, index_file)
    with open(path) as f:
        entries = json.load(f)

    changed = 0
    for e in entries:
        lp = local_path_for(e, device_type)
        if lp is None:
            continue
        blob = open(lp, "rb").read()
        want_size = len(blob)
        want_sha = hashlib.sha512(blob).hexdigest()
        if e["fileSize"] != want_size or e["sha512"] != want_sha:
            print(
                f"  {e['fileName']:44s} size {e['fileSize']} -> {want_size}"
                f"  sha {e['sha512'][:12]} -> {want_sha[:12]}"
            )
            e["fileSize"] = want_size
            e["sha512"] = want_sha
            changed += 1

    if changed:
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)
            f.write("\n")
    print(f"{index_file}: {changed} entries updated")
    return changed


if __name__ == "__main__":
    total = 0
    total += sync("zigbee2mqtt/ota/index_router.json", "router")
    total += sync("zigbee2mqtt/ota/index_router-FORCE.json", "router")
    total += sync("zigbee2mqtt/ota/index_end_device.json", "end_device")
    total += sync("zigbee2mqtt/ota/index_end_device-FORCE.json", "end_device")
    print(f"TOTAL: {total}")
    sys.exit(0)