#!/usr/bin/env python3
"""
Convert the upstream C# static data tables into Lua tables.

This is a mechanical translation of data only (model lists, weapon names,
component names, tints, colours, scenarios, timecycles). Logic is not touched.
"""
import re, os, sys, json

SRC = "/path/to/source/data"
OUT = "/mnt/user-data/outputs/retake2/data"
os.makedirs(OUT, exist_ok=True)

def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8-sig") as f:
        return f.read()

def strip_comments(block):
    # drop // comments and commented-out entries
    out = []
    for line in block.splitlines():
        s = line.split("//")[0]
        out.append(s)
    return "\n".join(out)

def block_after(text, header, open_ch="{", close_ch="}"):
    """Return the balanced {...} block that follows `header` in text."""
    i = text.find(header)
    if i < 0:
        return None
    j = text.find(open_ch, i + len(header))
    if j < 0:
        return None
    depth, k = 0, j
    while k < len(text):
        if text[k] == open_ch:
            depth += 1
        elif text[k] == close_ch:
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
        k += 1
    return None

def lua_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

# ── vehicles by class ────────────────────────────────────────────────────────
vd = read("VehicleData.cs")
classes = re.findall(r'public static List<string> (\w+)\s*{ get; }\s*=\s*new List<string>\(\)', vd)
vehicles = {}
for cls in classes:
    hdr = f'public static List<string> {cls} {{ get; }} = new List<string>()'
    blk = strip_comments(block_after(vd, hdr) or "")
    models = re.findall(r'"([^"]+)"', blk)
    if models:
        vehicles[cls] = models

# ── vehicle colours ──────────────────────────────────────────────────────────
colours = {}
for name in re.findall(r'public static readonly List<VehicleColor> (\w+) = new\(\)', vd):
    blk = strip_comments(block_after(vd, f'List<VehicleColor> {name} = new()') or "")
    entries = re.findall(r'new VehicleColor\(\s*(-?\d+)\s*,\s*"([^"]+)"\s*\)', blk)
    if entries:
        colours[name] = [(int(i), lbl) for i, lbl in entries]

# ── weapons ──────────────────────────────────────────────────────────────────
vw = read("ValidWeapon.cs")

wn_blk = strip_comments(block_after(vw, 'weaponNames = new()') or "")
weapons = re.findall(r'\{\s*"([^"]+)"\s*,\s*GetLabelText\("([^"]+)"\)\s*\}', wn_blk)

wd_blk = strip_comments(block_after(vw, 'weaponDescriptions = new()') or "")
descs = dict(re.findall(r'\["([^"]+)"\]\s*=\s*GetLabelText\("([^"]+)"\)', wd_blk))

wc_blk = strip_comments(block_after(vw, 'weaponComponentNames = new()') or "")
components = re.findall(r'\["([^"]+)"\]\s*=\s*GetLabelText\("([^"]+)"\)', wc_blk)

tints_blk = strip_comments(block_after(vw, 'WeaponTints = new()') or "")
tints = re.findall(r'\["([^"]+)"\]\s*=\s*(\d+)', tints_blk)

tints2_blk = strip_comments(block_after(vw, 'WeaponTintsMkII = new()') or "")
tints2 = re.findall(r'\["([^"]+)"\]\s*=\s*(\d+)', tints2_blk)

# ── scenarios ────────────────────────────────────────────────────────────────
ps = read("PedScenarios.cs")
scen_blk = strip_comments(block_after(ps, 'List<string> Scenarios = new()') or "")
scenarios = re.findall(r'"([^"]+)"', scen_blk)
pos_blk = strip_comments(block_after(ps, 'List<string> PositionBasedScenarios = new()') or "")
pos_scenarios = re.findall(r'"([^"]+)"', pos_blk)

# ── timecycles ───────────────────────────────────────────────────────────────
tc = read("TimeCycles.cs")
tc_blk = strip_comments(block_after(tc, 'List<string> Timecycles = new()') or "")
timecycles = re.findall(r'"([^"]+)"', tc_blk)

# ── animals ──────────────────────────────────────────────────────────────────
pm = read("PedModels.cs")
animals = re.findall(r'GenerateHashASCII\("([^"]+)"\)', pm)

# ── emit ─────────────────────────────────────────────────────────────────────
HEADER = ("-- AUTO-GENERATED data table. Data only, no logic.\n"
          "-- Regenerate with tools/build_data_tables.py.\n"
          "LMData = LMData or {}\n\n")

def write_lua(fname, body):
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(HEADER + body)

# vehicles
lines = ["LMData.Vehicles = {"]
for cls in sorted(vehicles):
    lines.append(f"    [{lua_str(cls)}] = {{")
    row = "        "
    for mdl in vehicles[cls]:
        piece = lua_str(mdl) + ", "
        if len(row) + len(piece) > 110:
            lines.append(row.rstrip())
            row = "        "
        row += piece
    lines.append(row.rstrip())
    lines.append("    },")
lines.append("}\n")
lines.append("LMData.VehicleClassOrder = {")
lines.append("    " + ", ".join(lua_str(c) for c in sorted(vehicles)))
lines.append("}\n")
write_lua("vehicles.lua", "\n".join(lines))

# colours
lines = ["LMData.VehicleColors = {"]
for name in sorted(colours):
    lines.append(f"    [{lua_str(name)}] = {{")
    for cid, lbl in colours[name]:
        lines.append(f"        {{ id = {cid}, label = {lua_str(lbl)} }},")
    lines.append("    },")
lines.append("}")
write_lua("vehicle_colors.lua", "\n".join(lines))

# weapons
lines = ["-- { spawn name, GTA label key }", "LMData.Weapons = {"]
for spawn, label in weapons:
    d = descs.get(spawn, "")
    lines.append(f"    {{ spawn = {lua_str(spawn)}, label = {lua_str(label)}"
                 + (f", desc = {lua_str(d)}" if d else "") + " },")
lines.append("}\n")
lines.append("-- component spawn name -> GTA label key. Availability per weapon is")
lines.append("-- checked at runtime with DoesWeaponTakeWeaponComponent.")
lines.append("LMData.WeaponComponents = {")
for comp, label in components:
    lines.append(f"    {{ comp = {lua_str(comp)}, label = {lua_str(label)} }},")
lines.append("}\n")
lines.append("LMData.WeaponTints = {")
for name, idx in tints:
    lines.append(f"    {{ label = {lua_str(name)}, index = {idx} }},")
lines.append("}\n")
lines.append("LMData.WeaponTintsMkII = {")
for name, idx in tints2:
    lines.append(f"    {{ label = {lua_str(name)}, index = {idx} }},")
lines.append("}")
write_lua("weapons.lua", "\n".join(lines))

# scenarios
lines = ["LMData.Scenarios = {"]
for s in scenarios:
    lines.append(f"    {lua_str(s)},")
lines.append("}\n")
lines.append("LMData.PositionBasedScenarios = {")
for s in pos_scenarios:
    lines.append(f"    {lua_str(s)},")
lines.append("}")
write_lua("scenarios.lua", "\n".join(lines))

# timecycles
lines = ["LMData.Timecycles = {"]
row = "    "
for t in timecycles:
    piece = lua_str(t) + ", "
    if len(row) + len(piece) > 110:
        lines.append(row.rstrip())
        row = "    "
    row += piece
lines.append(row.rstrip())
lines.append("}")
write_lua("timecycles.lua", "\n".join(lines))

# animals
lines = ["LMData.Animals = {"]
for a in animals:
    lines.append(f"    {lua_str(a)},")
lines.append("}")
write_lua("animals.lua", "\n".join(lines))

print(json.dumps({
    "vehicle_classes": {k: len(v) for k, v in sorted(vehicles.items())},
    "vehicle_models_total": sum(len(v) for v in vehicles.values()),
    "colour_sets": {k: len(v) for k, v in sorted(colours.items())},
    "weapons": len(weapons),
    "weapon_components": len(components),
    "tints": len(tints), "tints_mk2": len(tints2),
    "scenarios": len(scenarios), "position_scenarios": len(pos_scenarios),
    "timecycles": len(timecycles), "animals": len(animals),
}, indent=2))
