# fivem2sp

Run your FiveM Lua resources and ymap maps in GTA V single player. No OpenIV,
no `dlc.rpf`, no `mods` folder surgery for the script side.

It converts a resource folder into one plain `.lua` file that a Lua ASI plugin
loads directly. Edit your resource, re-run the converter, restart the script.

## What you need once

1. **ScriptHookV** in your GTA V root.
2. **A Lua plugin** — either:
   - [JM36 Lua Plugin (Reloaded)](https://www.gta5-mods.com/tools/jm36-lua-plugin-for-script-hook-v-reloaded) — written by an ex-FiveM scripter for exactly this, supports FiveM-style native calls, or
   - [LuaV](https://www.gta5-mods.com/tools/luav) — newer, LuaJIT, faster. Not script-compatible with the older plugins, but the shim covers the difference.
3. Python 3.9+ for the converter (runs on your PC, not in the game).

Output goes in the plugin's script folder (`scripts/addins/` for JM36, `lua/` for LuaV).

## Usage

```bash
# one resource
python -m fivem2sp "D:\FiveM\server-data\resources\my_shop" -o "D:\Games\GTAV\scripts\addins"

# a whole resources folder, including [category] subfolders
python -m fivem2sp "D:\FiveM\server-data\resources" -o "D:\Games\GTAV\scripts\addins"
```

Useful flags:

| flag | effect |
|---|---|
| `--no-server` | skip `server_scripts` instead of running them locally |
| `--no-maps` / `--no-scripts` | convert only one side |
| `--radius 450` | map streaming radius in metres (default 300) |
| `--no-quat-invert` | use if converted props come out rotated wrong |
| `--shared-shim` | one shared `fivem_shim.lua` instead of inlining it per bundle |

In game, the generated map scripts register console commands: `map_info`,
`map_tp`, `map_toggle`.

## How the script side works

`runtime/fivem_shim.lua` fakes the CitizenFX runtime:

- **Threads.** `Citizen.CreateThread` / `Wait` become coroutines, pumped from the
  plugin's `tick()` once per frame.
- **Events.** There is no network, so `TriggerServerEvent` dispatches straight
  into the server handlers loaded from the same resource, with `source = 1`,
  and `TriggerClientEvent` goes back the other way. Your client/server split
  keeps working — it just all happens in one Lua state.
- **Natives.** If the plugin only exposes the old `PLAYER.PLAYER_PED_ID()`
  namespaced style, the shim builds `PlayerPedId()`-style globals from it.
  The alias table near the top of the shim covers the common ones; add a line
  when a resource of yours calls something that isn't there.
- **Also provided:** `vector3`, `exports`, `RegisterCommand`, `json`,
  `SetResourceKvp*` backed by a flat file, and stubs for the network natives.

On-screen text is drawn at 0.72 scale in amber rather than the tiny default
white, so you can read it while driving. Change `shim.text` if you want
different.

## How the map side works

Instead of packing the ymap into an rpf so the streamer mounts it, the converter
reads the entity list at build time and the generated script spawns each prop at
runtime with `CREATE_OBJECT_NO_OFFSET`, sets rotation, freezes it, and streams
by distance so you are never holding thousands of objects.

**Input must be XML.** A raw `.ymap` is an RSC7-compressed resource. Open it in
CodeWalker, File > Export XML, and point the converter at the `.ymap.xml`. The
converter detects binary ymaps and tells you rather than emitting junk.

## The one thing this cannot do

Custom models. If your map resource ships `.ydr` / `.ytd` / `.yft` / `.ytyp`
files in a `stream/` folder, those archetypes do not exist in the game's files,
so `CREATE_OBJECT` returns 0 for them. Runtime spawning can only place props
the base game already has.

The converter flags this in two places: a warning at build time listing how many
custom asset files it found, and `map_info` in game printing every archetype
name that failed to resolve. Maps built out of vanilla props — most FiveM prop
placements — convert cleanly. MLO interiors and custom-model builds still need
their assets mounted, and that is the one job OpenIV or an equivalent still has.

## What won't convert

The converter warns on these rather than silently producing something broken:

- ESX / QBCore framework calls — those resources expect a framework, not a game
- `MySQL` / `oxmysql` — no database
- NUI (`SendNUIMessage`, `RegisterNUICallback`) — no CEF layer in SP
- `PerformHttpRequest`
- `@other-resource/file.lua` includes — convert that resource too

## GTA 6

The map half of this is the part that ports. Reading a map format and
re-creating it through whatever object-spawning API exists is not tied to
ScriptHookV; only the shim's native layer is. When a script hook for VI lands,
the alias table is the file to rewrite.
