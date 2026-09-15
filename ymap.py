"""Read CodeWalker-exported .ymap.xml files into a flat entity list.

Binary .ymap files are RSC7-compressed resources. We detect them and say
so plainly rather than emitting garbage -- CodeWalker exports XML in two
clicks, and that is the input this tool wants.
"""

from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass

RSC7_MAGIC = b"RSC7"


@dataclass
class Entity:
    archetype: str
    x: float
    y: float
    z: float
    # euler degrees, GTA order (pitch, roll, yaw)
    rx: float
    ry: float
    rz: float
    lod_dist: float = 500.0
    flags: int = 0
    source: str = ""


@dataclass
class MapData:
    name: str
    entities: list[Entity]
    deletions: list[tuple[str, float, float, float]]


class BinaryYmapError(RuntimeError):
    pass


def _f(node, attr: str, default: float = 0.0) -> float:
    if node is None:
        return default
    v = node.get(attr)
    if v is None:
        v = node.get("value")
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def quat_to_euler_zxy(x: float, y: float, z: float, w: float) -> tuple[float, float, float]:
    """Quaternion -> euler degrees in the ZXY order SET_ENTITY_ROTATION(.., 2) wants."""
    sinp = 2.0 * (w * x - y * z)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)
    roll = math.atan2(2.0 * (w * y + z * x), 1.0 - 2.0 * (x * x + y * y))
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (x * x + z * z))
    d = 180.0 / math.pi
    return pitch * d, roll * d, yaw * d


def is_binary_ymap(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == RSC7_MAGIC
    except OSError:
        return False


def parse_ymap_xml(path: str, invert_quat: bool = True) -> MapData:
    if is_binary_ymap(path):
        raise BinaryYmapError(
            f"{os.path.basename(path)} is a binary (RSC7) ymap. "
            "Open it in CodeWalker and use File > Export XML, then point this tool "
            "at the resulting .ymap.xml."
        )

    tree = ET.parse(path)
    root = tree.getroot()
    name = os.path.splitext(os.path.basename(path))[0].replace(".ymap", "")

    entities: list[Entity] = []
    for item in root.findall("./entities/Item"):
        arch = item.findtext("archetypeName", default="").strip()
        if not arch:
            continue
        pos = item.find("position")
        rot = item.find("rotation")

        qx, qy, qz = _f(rot, "x"), _f(rot, "y"), _f(rot, "z")
        qw = _f(rot, "w", 1.0)
        # CEntityDef stores the conjugate of the visual rotation, so the
        # quaternion is inverted before conversion. If a converted map comes
        # out with props rotated the wrong way, pass invert_quat=False
        # (--no-quat-invert on the CLI) and rebuild.
        if invert_quat:
            qx, qy, qz = -qx, -qy, -qz
        rx, ry, rz = quat_to_euler_zxy(qx, qy, qz, qw)

        lod = item.find("lodDist")
        entities.append(
            Entity(
                archetype=arch,
                x=_f(pos, "x"),
                y=_f(pos, "y"),
                z=_f(pos, "z"),
                rx=rx,
                ry=ry,
                rz=rz,
                lod_dist=_f(lod, "value", 500.0) if lod is not None else 500.0,
                flags=int(_f(item.find("flags"), "value", 0.0)),
                source=os.path.basename(path),
            )
        )

    deletions: list[tuple[str, float, float, float]] = []
    for node_name in ("./entities/Item[@type='CEntityDef']", ):
        pass
    # occluders / deleted entity lists appear under a few tag names
    for tag in ("physicsDictionaries", ):
        pass
    for item in root.findall("./deletedEntities/Item") + root.findall("./removedEntities/Item"):
        arch = item.findtext("archetypeName", default="").strip()
        pos = item.find("position")
        if arch:
            deletions.append((arch, _f(pos, "x"), _f(pos, "y"), _f(pos, "z")))

    return MapData(name=name, entities=entities, deletions=deletions)


def collect_maps(paths: list[str], invert_quat: bool = True) -> tuple[list[MapData], list[str]]:
    """Returns (parsed maps, warnings)."""
    maps, warnings = [], []
    for p in paths:
        try:
            md = parse_ymap_xml(p, invert_quat=invert_quat)
            if not md.entities:
                warnings.append(f"{os.path.basename(p)}: no entities found, skipped")
                continue
            maps.append(md)
        except BinaryYmapError as e:
            warnings.append(str(e))
        except ET.ParseError as e:
            warnings.append(f"{os.path.basename(p)}: XML parse error ({e})")
    return maps, warnings
