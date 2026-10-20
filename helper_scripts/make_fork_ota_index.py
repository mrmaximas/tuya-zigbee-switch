#!/usr/bin/env python3
"""Generate a Z2M OTA index that serves artifacts from a git fork.

Zigbee2MQTT verifies fileSize + sha512 against the index entry before
handing the file to the coordinator. The upstream index
(`zigbee2mqtt/ota/index_router*.json`) points at romasku's `main`, which
holds a build without the countdown timer, so it can never serve the
locally built binaries. This rewrites the `url` of every locally
present artifact to the fork and the owning branch, then writes the
result as a separate index file.

The upstream index files are left untouched — the originals must keep
working for everyone else.

Usage:
    python3 helper_scripts/make_fork_ota_index.py \
        --fork mrmaximas/tuya-zigbee-switch \
        --branch feat/on-with-timed-off-timer

Then point Z2M at the generated file:

    zigbee_ota_override_index_location:
      https://raw.githubusercontent.com/<fork>/<branch>/zigbee2mqtt/ota/index_router-fork.json
"""
import argparse
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/{fork}/{branch}"


def board_dir(entry):
    m = re.search(r"/bin/([a-z_]+)/([A-Za-z0-9_]+)/([^/]+)$", entry["url"])
    return m.groups() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fork", required=True, help="owner/repo of the fork")
    ap.add_argument("--branch", required=True, help="branch holding bin/")
    ap.add_argument("--suffix", default="-fork", help="index filename suffix")
    ap.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="BOARD",
        help="only rewrite entries for this board dir (repeatable). "
        "Without it every board whose artifact happens to exist "
        "locally is rewritten, which is almost always more than you "
        "rebuilt — point the fork index at the boards you actually "
        "produced.",
    )
    args = ap.parse_args()

    base = RAW.format(fork=args.fork, branch=args.branch)
    wanted = set(args.only or [])

    for src_name in ("index_router.json", "index_router-FORCE.json"):
        src = os.path.join(ROOT, "zigbee2mqtt/ota", src_name)
        dst_name = src_name.replace(".json", f"{args.suffix}.json")
        dst = os.path.join(ROOT, "zigbee2mqtt/ota", dst_name)

        with open(src) as f:
            entries = json.load(f)

        rewritten = 0
        for e in entries:
            parts = board_dir(e)
            if not parts:
                continue
            device_type, board, filename = parts
            if wanted and board not in wanted:
                continue
            local = os.path.join(ROOT, "bin", device_type, board, filename)
            if not os.path.isfile(local):
                continue  # never built locally — keep the upstream URL
            blob = open(local, "rb").read()
            e["fileSize"] = len(blob)
            e["sha512"] = hashlib.sha512(blob).hexdigest()
            e["url"] = f"{base}/bin/{device_type}/{board}/{filename}"
            rewritten += 1

        with open(dst, "w") as f:
            json.dump(entries, f, indent=2)
            f.write("\n")

        print(f"{dst_name}: {rewritten} entries pointed at {args.fork}@{args.branch}")
        print(f"  → point Z2M at: {base}/zigbee2mqtt/ota/{dst_name}")


if __name__ == "__main__":
    main()