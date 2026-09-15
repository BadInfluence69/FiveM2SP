"""fivem2sp - convert FiveM resources into GTA V single-player Lua.

Usage:
    python -m fivem2sp <resource-or-parent-dir> [...] -o <scripts/addins>
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

from .bundler import bundle_resource
from .manifest import expand_globs, find_manifest, parse_manifest
from .mapgen import generate_map_lua
from .ymap import collect_maps

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM_PATH = os.path.join(HERE, "..", "runtime", "fivem_shim.lua")

C_OK, C_WARN, C_ERR, C_DIM, C_OFF = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[0m"


def _c(text: str, colour: str) -> str:
    return text if os.environ.get("NO_COLOR") else f"{colour}{text}{C_OFF}"


def load_shim() -> str:
    path = os.path.normpath(SHIM_PATH)
    if not os.path.isfile(path):
        sys.exit(f"cannot find fivem_shim.lua (looked in {path})")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def discover_resources(root: str) -> list[str]:
    """A resource dir has a manifest. Otherwise treat root as a parent."""
    if find_manifest(root):
        return [root]
    found = []
    for entry in sorted(os.listdir(root)):
        sub = os.path.join(root, entry)
        if os.path.isdir(sub):
            if find_manifest(sub):
                found.append(sub)
            else:
                # one more level, for [categories] folders
                for entry2 in sorted(os.listdir(sub)):
                    sub2 = os.path.join(sub, entry2)
                    if os.path.isdir(sub2) and find_manifest(sub2):
                        found.append(sub2)
    return found


def ymaps_in(resource_dir: str, mf) -> list[str]:
    hits = set(expand_globs(resource_dir, [f for f in mf.files if ".ymap" in f.lower()]))
    for pat in ("**/*.ymap.xml", "**/*.ymap"):
        hits.update(
            p for p in glob.glob(os.path.join(resource_dir, pat), recursive=True)
            if os.path.isfile(p)
        )
    # prefer the .xml version when both exist
    xml = {p for p in hits if p.lower().endswith(".xml")}
    stems = {p[: -len(".xml")] for p in xml}
    return sorted(xml | {p for p in hits if p not in stems and not p.lower().endswith(".xml")})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fivem2sp", description=__doc__)
    ap.add_argument("sources", nargs="+", help="resource folder(s), or a resources/ parent folder")
    ap.add_argument("-o", "--out", required=True, help="output folder (your plugin's scripts/addins)")
    ap.add_argument("--no-server", action="store_true", help="skip server_scripts instead of running them locally")
    ap.add_argument("--no-maps", action="store_true", help="skip ymap conversion")
    ap.add_argument("--no-scripts", action="store_true", help="only convert maps")
    ap.add_argument("--radius", type=float, default=300.0, help="map streaming radius in metres (default 300)")
    ap.add_argument("--no-quat-invert", action="store_true",
                    help="do not conjugate ymap rotation quaternions (use if props come out mis-rotated)")
    ap.add_argument("--shared-shim", action="store_true",
                    help="load fivem_shim.lua by dofile instead of inlining it into each bundle")
    args = ap.parse_args(argv)

    shim = load_shim()
    inline = not args.shared_shim
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    if args.shared_shim:
        with open(os.path.join(out, "fivem_shim.lua"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(shim)

    resources: list[str] = []
    for src in args.sources:
        src = os.path.abspath(src)
        if not os.path.isdir(src):
            print(_c(f"not a directory: {src}", C_ERR))
            continue
        resources.extend(discover_resources(src))

    if not resources:
        print(_c("no resources found (looked for fxmanifest.lua / __resource.lua)", C_ERR))
        return 1

    total_warn = 0
    for rdir in resources:
        mpath = find_manifest(rdir)
        mf = parse_manifest(mpath)
        print(_c(f"\n== {mf.resource_name}", C_OK) + _c(f"  ({rdir})", C_DIM))

        if not args.no_scripts and (mf.all_scripts or mf.server_scripts):
            res = bundle_resource(mf, out, shim,
                                  include_server=not args.no_server,
                                  inline_shim=inline)
            print(f"   scripts : {res.script_count} client/shared, {res.server_count} server "
                  f"-> {os.path.basename(res.out_path)}")
            for n in res.notes:
                print(_c(f"   note    : {n}", C_DIM))
            for w in res.warnings:
                total_warn += 1
                print(_c(f"   warn    : {w}", C_WARN))

        if not args.no_maps:
            ym = ymaps_in(rdir, mf)
            if ym:
                maps, warns = collect_maps(ym, invert_quat=not args.no_quat_invert)
                for w in warns:
                    total_warn += 1
                    print(_c(f"   warn    : {w}", C_WARN))
                if maps:
                    path, n = generate_map_lua(maps, out, mf.resource_name, shim,
                                               stream_radius=args.radius,
                                               inline_shim=inline)
                    print(f"   map     : {n} entities from {len(maps)} ymap(s) "
                          f"-> {os.path.basename(path)}")

        stream_assets = [
            f for f in glob.glob(os.path.join(rdir, "**", "*"), recursive=True)
            if os.path.splitext(f)[1].lower() in (".ydr", ".ydd", ".ytd", ".yft", ".ybn", ".ytyp")
        ]
        if stream_assets:
            total_warn += 1
            print(_c(f"   warn    : {len(stream_assets)} custom asset file(s) in this resource "
                     f"(.ydr/.ytd/.ytyp etc). Runtime spawning cannot register these; "
                     f"only vanilla archetypes will appear.", C_WARN))

    print(_c(f"\ndone -> {out}", C_OK))
    if total_warn:
        print(_c(f"{total_warn} warning(s) above - read them, they are the parts that need a decision.", C_WARN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
