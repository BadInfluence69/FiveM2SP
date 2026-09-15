"""Parse fxmanifest.lua / __resource.lua without running Lua.

We only care about the declarative directives a map or script resource
uses, so a tokeniser over the common forms is enough:

    client_script 'x.lua'
    client_scripts { 'a.lua', 'b.lua' }
    files { 'stream/thing.ymap' }
    this_is_a_map 'yes'
    data_file 'DLC_ITYP_REQUEST' 'stream/thing.ytyp'
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# directive followed by either a quoted string or a { ... } list
_DIRECTIVE = re.compile(
    r"""^[ \t]*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)[ \t]*
        (?:\(\s*)?
        (?P<body>'[^']*'|"[^"]*"|\{)""",
    re.VERBOSE | re.MULTILINE,
)

_STRING = re.compile(r"""'([^']*)'|"([^"]*)\"""")

LIST_DIRECTIVES = {
    "client_script", "client_scripts",
    "server_script", "server_scripts",
    "shared_script", "shared_scripts",
    "file", "files",
    "ui_page", "dependency", "dependencies",
    "escrow_ignore",
}


@dataclass
class Manifest:
    path: str
    resource_name: str
    client_scripts: list[str] = field(default_factory=list)
    server_scripts: list[str] = field(default_factory=list)
    shared_scripts: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    data_files: list[tuple[str, str]] = field(default_factory=list)
    is_map: bool = False
    fx_version: str | None = None
    game: str | None = None
    raw_directives: dict = field(default_factory=dict)

    @property
    def all_scripts(self) -> list[str]:
        """Load order FiveM uses: shared, then client. Server handled apart."""
        return self.shared_scripts + self.client_scripts


def _strip_comments(text: str) -> str:
    text = re.sub(r"--\[\[.*?\]\]", "", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", text)


def _balanced_block(text: str, open_idx: int) -> str:
    depth, i = 0, open_idx
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]
        i += 1
    return text[open_idx:]


def _strings_in(chunk: str) -> list[str]:
    return [a or b for a, b in _STRING.findall(chunk)]


def parse_manifest(path: str) -> Manifest:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = _strip_comments(fh.read())

    resource_dir = os.path.dirname(os.path.abspath(path))
    mf = Manifest(path=path, resource_name=os.path.basename(resource_dir))

    for m in _DIRECTIVE.finditer(text):
        name = m.group("name")
        body = m.group("body")

        if body == "{":
            chunk = _balanced_block(text, m.start("body"))
            values = _strings_in(chunk)
        else:
            values = _strings_in(body)
            # data_file takes two strings on one line
            tail = text[m.end("body") : m.end("body") + 200].split("\n", 1)[0]
            extra = _strings_in(tail)
            if name == "data_file" and extra:
                values = values + extra[:1]

        mf.raw_directives.setdefault(name, []).extend(values)

        if name in ("client_script", "client_scripts"):
            mf.client_scripts += values
        elif name in ("server_script", "server_scripts"):
            mf.server_scripts += values
        elif name in ("shared_script", "shared_scripts"):
            mf.shared_scripts += values
        elif name in ("file", "files"):
            mf.files += values
        elif name == "data_file" and len(values) >= 2:
            mf.data_files.append((values[0], values[1]))
        elif name == "this_is_a_map":
            mf.is_map = True
        elif name == "fx_version":
            mf.fx_version = values[0] if values else None
        elif name == "game":
            mf.game = values[0] if values else None

    return mf


def find_manifest(resource_dir: str) -> str | None:
    for candidate in ("fxmanifest.lua", "__resource.lua"):
        p = os.path.join(resource_dir, candidate)
        if os.path.isfile(p):
            return p
    return None


def expand_globs(resource_dir: str, patterns: list[str]) -> list[str]:
    """Resolve FiveM's '@' prefixes and '*' / '**' globs to real files."""
    import glob as _glob

    out: list[str] = []
    for pat in patterns:
        if pat.startswith("@"):
            continue  # cross-resource include; handled by the bundler warning
        full = os.path.join(resource_dir, pat)
        if any(ch in pat for ch in "*?["):
            hits = sorted(_glob.glob(full, recursive=True))
            out.extend(h for h in hits if os.path.isfile(h))
        elif os.path.isfile(full):
            out.append(full)
    seen, uniq = set(), []
    for p in out:
        rp = os.path.normpath(p)
        if rp not in seen:
            seen.add(rp)
            uniq.append(rp)
    return uniq
