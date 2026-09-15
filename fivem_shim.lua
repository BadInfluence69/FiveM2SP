--[[
  fivem_shim.lua  --  FiveM -> GTA V single player compatibility layer
  ------------------------------------------------------------------
  Target: JM36 Lua Plugin (Reloaded) or LuaV, both under ScriptHookV.

  This file is prepended to every bundle produced by fivem2sp. It fakes
  enough of the CitizenFX runtime that ordinary client/server Lua from a
  FiveM resource will run in single player, in ONE Lua state, with the
  "server" living in the same process as the "client".

  Drop this in the plugin's scripts folder. Bundles require it by name.
]]--

if _G.__FIVEM_SHIM then return _G.__FIVEM_SHIM end

local shim = {}
_G.__FIVEM_SHIM = shim

-- ===================================================================
-- 1. NATIVE CALL NORMALISATION
-- ===================================================================
-- Legacy Lua Plugin exposes natives as PLAYER.PLAYER_PED_ID().
-- JM36 Reloaded and LuaV also expose FiveM-style globals: PlayerPedId().
-- We detect which we have and fill in the gaps so resource code that
-- calls PlayerPedId() works either way.

local HAS_NAMESPACED = (type(_G.PLAYER) == "table" and _G.PLAYER.PLAYER_PED_ID ~= nil)
local HAS_FIVEM_STYLE = (type(_G.PlayerPedId) == "function")

shim.runtime = HAS_FIVEM_STYLE and "fivem-style" or (HAS_NAMESPACED and "namespaced" or "unknown")

-- name mapping: FiveM-style global  ->  { NAMESPACE, NATIVE_NAME }
-- Extend this table when a resource of yours calls something missing.
local ALIASES = {
    PlayerPedId              = {"PLAYER", "PLAYER_PED_ID"},
    PlayerId                 = {"PLAYER", "PLAYER_ID"},
    GetPlayerPed             = {"PLAYER", "GET_PLAYER_PED"},
    GetPlayerName            = {"PLAYER", "GET_PLAYER_NAME"},
    GetEntityCoords          = {"ENTITY", "GET_ENTITY_COORDS"},
    GetEntityHeading         = {"ENTITY", "GET_ENTITY_HEADING"},
    GetEntityRotation        = {"ENTITY", "GET_ENTITY_ROTATION"},
    SetEntityCoords          = {"ENTITY", "SET_ENTITY_COORDS"},
    SetEntityCoordsNoOffset  = {"ENTITY", "SET_ENTITY_COORDS_NO_OFFSET"},
    SetEntityRotation        = {"ENTITY", "SET_ENTITY_ROTATION"},
    SetEntityHeading         = {"ENTITY", "SET_ENTITY_HEADING"},
    DoesEntityExist          = {"ENTITY", "DOES_ENTITY_EXIST"},
    DeleteEntity             = {"ENTITY", "DELETE_ENTITY"},
    FreezeEntityPosition     = {"ENTITY", "FREEZE_ENTITY_POSITION"},
    SetEntityInvincible      = {"ENTITY", "SET_ENTITY_INVINCIBLE"},
    SetEntityAsMissionEntity = {"ENTITY", "SET_ENTITY_AS_MISSION_ENTITY"},
    SetEntityLodDist         = {"ENTITY", "SET_ENTITY_LOD_DIST"},
    SetEntityCollision       = {"ENTITY", "SET_ENTITY_COLLISION"},
    IsEntityDead             = {"ENTITY", "IS_ENTITY_DEAD"},
    GetEntityHealth          = {"ENTITY", "GET_ENTITY_HEALTH"},
    SetEntityHealth          = {"ENTITY", "SET_ENTITY_HEALTH"},
    GetEntityModel           = {"ENTITY", "GET_ENTITY_MODEL"},

    CreateObject             = {"OBJECT", "CREATE_OBJECT"},
    CreateObjectNoOffset     = {"OBJECT", "CREATE_OBJECT_NO_OFFSET"},
    DeleteObject             = {"OBJECT", "DELETE_OBJECT"},

    CreatePed                = {"PED", "CREATE_PED"},
    DeletePed                = {"PED", "DELETE_PED"},
    IsPedInAnyVehicle        = {"PED", "IS_PED_IN_ANY_VEHICLE"},
    GetVehiclePedIsIn        = {"PED", "GET_VEHICLE_PED_IS_IN"},
    SetPedComponentVariation = {"PED", "SET_PED_COMPONENT_VARIATION"},
    TaskGoToCoordAnyMeans    = {"TASK", "TASK_GO_TO_COORD_ANY_MEANS"},

    CreateVehicle            = {"VEHICLE", "CREATE_VEHICLE"},
    DeleteVehicle            = {"VEHICLE", "DELETE_VEHICLE"},
    SetVehicleNumberPlateText= {"VEHICLE", "SET_VEHICLE_NUMBER_PLATE_TEXT"},
    SetVehicleEngineOn       = {"VEHICLE", "SET_VEHICLE_ENGINE_ON"},
    GetVehicleNumberPlateText= {"VEHICLE", "GET_VEHICLE_NUMBER_PLATE_TEXT"},

    RequestModel             = {"STREAMING", "REQUEST_MODEL"},
    HasModelLoaded           = {"STREAMING", "HAS_MODEL_LOADED"},
    SetModelAsNoLongerNeeded = {"STREAMING", "SET_MODEL_AS_NO_LONGER_NEEDED"},
    IsModelValid             = {"STREAMING", "IS_MODEL_VALID"},
    IsModelInCdimage         = {"STREAMING", "IS_MODEL_IN_CDIMAGE"},
    RequestAnimDict          = {"STREAMING", "REQUEST_ANIM_DICT"},
    HasAnimDictLoaded        = {"STREAMING", "HAS_ANIM_DICT_LOADED"},

    GetHashKey               = {"MISC", "GET_HASH_KEY"},
    GetGameTimer             = {"MISC", "GET_GAME_TIMER"},
    GetDistanceBetweenCoords = {"MISC", "GET_DISTANCE_BETWEEN_COORDS"},
    CreateModelHide          = {"MISC", "CREATE_MODEL_HIDE"},
    RemoveModelHide          = {"MISC", "REMOVE_MODEL_HIDE"},
    GetGroundZFor_3dCoord    = {"MISC", "GET_GROUND_Z_FOR_3D_COORD"},

    SetTextFont              = {"UI", "SET_TEXT_FONT"},
    SetTextScale             = {"UI", "SET_TEXT_SCALE"},
    SetTextColour            = {"UI", "SET_TEXT_COLOUR"},
    SetTextOutline           = {"UI", "SET_TEXT_OUTLINE"},
    SetTextDropShadow        = {"UI", "SET_TEXT_DROP_SHADOW"},
    SetTextCentre            = {"UI", "SET_TEXT_CENTRE"},
    DrawRect                 = {"GRAPHICS", "DRAW_RECT"},
    DrawMarker               = {"GRAPHICS", "DRAW_MARKER"},

    AddBlipForCoord          = {"UI", "ADD_BLIP_FOR_COORD"},
    SetBlipSprite            = {"UI", "SET_BLIP_SPRITE"},
    SetBlipColour            = {"UI", "SET_BLIP_COLOUR"},
    SetBlipScale             = {"UI", "SET_BLIP_SCALE"},
    SetBlipAsShortRange      = {"UI", "SET_BLIP_AS_SHORT_RANGE"},
    RemoveBlip               = {"UI", "REMOVE_BLIP"},

    IsControlJustPressed     = {"CONTROLS", "IS_CONTROL_JUST_PRESSED"},
    IsControlPressed         = {"CONTROLS", "IS_CONTROL_PRESSED"},
    DisableControlAction     = {"CONTROLS", "DISABLE_CONTROL_ACTION"},
}

if HAS_NAMESPACED then
    for global_name, pair in pairs(ALIASES) do
        if _G[global_name] == nil then
            local ns, fn = pair[1], pair[2]
            local nstbl = _G[ns]
            if type(nstbl) == "table" and type(nstbl[fn]) == "function" then
                _G[global_name] = nstbl[fn]
            end
        end
    end
end

-- Report anything a script asks for that we could not provide, instead of
-- dying with "attempt to call a nil value" three hours into a session.
shim.missing = {}
function shim.require_native(name)
    if type(_G[name]) ~= "function" then
        shim.missing[name] = true
        return false
    end
    return true
end

-- ===================================================================
-- 2. vector3 / vector2
-- ===================================================================
if type(_G.vector3) ~= "function" then
    local vmt = {}
    vmt.__index = vmt
    vmt.__add = function(a, b) return vector3(a.x + b.x, a.y + b.y, a.z + b.z) end
    vmt.__sub = function(a, b) return vector3(a.x - b.x, a.y - b.y, a.z - b.z) end
    vmt.__mul = function(a, b)
        if type(b) == "number" then return vector3(a.x * b, a.y * b, a.z * b) end
        if type(a) == "number" then return vector3(b.x * a, b.y * a, b.z * a) end
        return vector3(a.x * b.x, a.y * b.y, a.z * b.z)
    end
    vmt.__eq = function(a, b) return a.x == b.x and a.y == b.y and a.z == b.z end
    vmt.__tostring = function(v)
        return string.format("vector3(%.3f, %.3f, %.3f)", v.x, v.y, v.z)
    end
    vmt.__len = function(v) return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) end

    function _G.vector3(x, y, z)
        return setmetatable({ x = x or 0.0, y = y or 0.0, z = z or 0.0 }, vmt)
    end
    function _G.vector2(x, y) return _G.vector3(x, y, 0.0) end
    shim.vector_mt = vmt
end

function _G.GetDistanceBetweenVectors(a, b)
    local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

-- ===================================================================
-- 3. COOPERATIVE SCHEDULER  (Citizen.CreateThread / Wait / SetTimeout)
-- ===================================================================
local threads = {}
local timers = {}
local thread_seq = 0

local function now_ms()
    if type(_G.GetGameTimer) == "function" then return GetGameTimer() end
    return math.floor(os.clock() * 1000)
end
shim.now_ms = now_ms

local Citizen = _G.Citizen or {}
_G.Citizen = Citizen
_G.CFX = Citizen

function Citizen.CreateThread(fn)
    thread_seq = thread_seq + 1
    local t = {
        id = thread_seq,
        co = coroutine.create(fn),
        wake = 0,
    }
    threads[#threads + 1] = t
    return t.id
end

function Citizen.Wait(ms)
    coroutine.yield(ms or 0)
end

function Citizen.SetTimeout(ms, fn)
    timers[#timers + 1] = { at = now_ms() + (ms or 0), fn = fn }
end

function Citizen.Trace(msg)
    print("[fivem2sp] " .. tostring(msg))
end

_G.CreateThread = Citizen.CreateThread
_G.Wait         = Citizen.Wait
_G.SetTimeout   = Citizen.SetTimeout

-- Pumped once per frame from tick(). Returns the number of live threads.
function shim.pump()
    local t_now = now_ms()

    local i = 1
    while i <= #timers do
        local tm = timers[i]
        if t_now >= tm.at then
            table.remove(timers, i)
            local ok, err = pcall(tm.fn)
            if not ok then print("[fivem2sp] timer error: " .. tostring(err)) end
        else
            i = i + 1
        end
    end

    i = 1
    while i <= #threads do
        local t = threads[i]
        if coroutine.status(t.co) == "dead" then
            table.remove(threads, i)
        elseif t_now >= t.wake then
            local ok, res = coroutine.resume(t.co)
            if not ok then
                print("[fivem2sp] thread " .. t.id .. " error: " .. tostring(res))
                table.remove(threads, i)
            else
                if coroutine.status(t.co) == "dead" then
                    table.remove(threads, i)
                else
                    t.wake = t_now + (tonumber(res) or 0)
                    i = i + 1
                end
            end
        else
            i = i + 1
        end
    end

    return #threads
end

-- ===================================================================
-- 4. EVENT BUS  (client <-> "server" loopback in one process)
-- ===================================================================
-- In single player there is no network. TriggerServerEvent dispatches
-- straight into the server-side handlers registered by the same bundle,
-- with `source` set to 1. TriggerClientEvent goes the other way.

local handlers = { client = {}, server = {} }
shim.side = "client"   -- flipped by the bundler while loading server files

local function add_handler(side, name, fn)
    handlers[side][name] = handlers[side][name] or {}
    table.insert(handlers[side][name], fn)
end

local function dispatch(side, name, src, ...)
    local list = handlers[side][name]
    if not list then return false end
    local prev_source = _G.source
    _G.source = src
    for _, fn in ipairs(list) do
        local ok, err = pcall(fn, ...)
        if not ok then
            print("[fivem2sp] handler '" .. name .. "' error: " .. tostring(err))
        end
    end
    _G.source = prev_source
    return true
end

function _G.RegisterNetEvent(name, fn)
    if fn then add_handler(shim.side, name, fn) end
end

function _G.RegisterServerEvent(name, fn)
    if fn then add_handler("server", name, fn) end
end

function _G.AddEventHandler(name, fn)
    add_handler(shim.side, name, fn)
    return { name = name }
end

function _G.RemoveEventHandler(ref)
    if type(ref) == "table" and ref.name then
        handlers[shim.side][ref.name] = nil
    end
end

function _G.TriggerEvent(name, ...)
    return dispatch(shim.side, name, 1, ...)
end

function _G.TriggerServerEvent(name, ...)
    return dispatch("server", name, 1, ...)
end

function _G.TriggerClientEvent(name, target, ...)
    -- FiveM signature is (name, source, ...). In SP the target is always us.
    return dispatch("client", name, 1, ...)
end

_G.TriggerLatentServerEvent = function(name, _bps, ...) return TriggerServerEvent(name, ...) end
_G.TriggerLatentClientEvent = function(name, target, _bps, ...) return TriggerClientEvent(name, target, ...) end

-- ===================================================================
-- 5. EXPORTS
-- ===================================================================
local export_store = {}
shim.exports = export_store

function _G.exports__register(resource, name, fn)
    export_store[resource] = export_store[resource] or {}
    export_store[resource][name] = fn
end

_G.exports = setmetatable({}, {
    __index = function(_, resource)
        return setmetatable({}, {
            __index = function(_, fname)
                return function(_, ...)
                    local r = export_store[resource]
                    local fn = r and r[fname]
                    if not fn then
                        print(("[fivem2sp] missing export %s:%s"):format(resource, fname))
                        return nil
                    end
                    return fn(...)
                end
            end
        })
    end
})

-- ===================================================================
-- 6. RESOURCE / KVP / MISC STUBS
-- ===================================================================
shim.current_resource = "fivem2sp"

function _G.GetCurrentResourceName() return shim.current_resource end
function _G.GetResourceState() return "started" end
function _G.IsDuplicityVersion() return shim.side == "server" end
function _G.GetPlayers() return { 1 } end
function _G.GetPlayerIdentifiers() return { "license:singleplayer" } end
function _G.NetworkGetEntityFromNetworkId(id) return id end
function _G.NetworkGetNetworkIdFromEntity(e) return e end
function _G.NetworkRequestControlOfEntity() return true end
function _G.NetworkHasControlOfEntity() return true end
function _G.DecorSetInt() return true end
function _G.DecorRegister() return true end

-- Key/value store, backed by a flat file if the plugin exposes io.
local KVP_FILE = "fivem2sp_kvp.txt"
local kvp = {}
do
    local ok = pcall(function()
        local f = io.open(KVP_FILE, "r")
        if f then
            for line in f:lines() do
                local k, v = line:match("^([^\t]+)\t(.*)$")
                if k then kvp[k] = v end
            end
            f:close()
        end
    end)
    shim.kvp_persistent = ok and (io ~= nil)
end

local function kvp_flush()
    pcall(function()
        local f = io.open(KVP_FILE, "w")
        if not f then return end
        for k, v in pairs(kvp) do f:write(k .. "\t" .. tostring(v) .. "\n") end
        f:close()
    end)
end

function _G.SetResourceKvp(k, v) kvp[k] = tostring(v); kvp_flush() end
function _G.SetResourceKvpInt(k, v) kvp[k] = tostring(v); kvp_flush() end
function _G.SetResourceKvpFloat(k, v) kvp[k] = tostring(v); kvp_flush() end
function _G.GetResourceKvpString(k) return kvp[k] end
function _G.GetResourceKvpInt(k) return tonumber(kvp[k]) or 0 end
function _G.GetResourceKvpFloat(k) return tonumber(kvp[k]) or 0.0 end
function _G.DeleteResourceKvp(k) kvp[k] = nil; kvp_flush() end

-- Commands: registered names are callable from the plugin console, and
-- also exposed on shim.commands so you can bind them to a key yourself.
shim.commands = {}
function _G.RegisterCommand(name, fn, restricted)
    shim.commands[name] = fn
end
function shim.run_command(name, ...)
    local fn = shim.commands[name]
    if not fn then
        print("[fivem2sp] no such command: " .. tostring(name))
        return false
    end
    local ok, err = pcall(fn, 1, { ... }, name)
    if not ok then print("[fivem2sp] command error: " .. tostring(err)) end
    return ok
end

-- ===================================================================
-- 7. ON-SCREEN TEXT
-- ===================================================================
-- Deliberately large and amber rather than the tiny default white, so it
-- is readable at a glance while you are actually driving around testing.
shim.text = {
    scale   = 0.72,   -- roughly 22-24pt at 1080p
    font    = 4,
    colour  = { 255, 186, 64, 235 },   -- amber
    shadow  = true,
}

local function begin_text()
    if not shim.require_native("SetTextFont") then return false end
    SetTextFont(shim.text.font)
    SetTextScale(shim.text.scale, shim.text.scale)
    local c = shim.text.colour
    SetTextColour(c[1], c[2], c[3], c[4])
    if shim.text.shadow then
        SetTextDropShadow(0, 0, 0, 0, 255)
        SetTextOutline()
    end
    return true
end

function shim.draw_text(x, y, str)
    if not begin_text() then return end
    if type(_G.UI) == "table" and UI._SET_TEXT_ENTRY then
        UI._SET_TEXT_ENTRY("STRING")
        UI._ADD_TEXT_COMPONENT_STRING(tostring(str))
        UI._DRAW_TEXT(x, y)
    elseif type(_G.SetTextEntry) == "function" then
        SetTextEntry("STRING")
        AddTextComponentString(tostring(str))
        DrawText(x, y)
    elseif type(_G.BeginTextCommandDisplayText) == "function" then
        BeginTextCommandDisplayText("STRING")
        AddTextComponentSubstringPlayerName(tostring(str))
        EndTextCommandDisplayText(x, y)
    end
end

local notifications = {}
function shim.notify(msg, ms)
    notifications[#notifications + 1] = { msg = tostring(msg), until_ms = now_ms() + (ms or 4000) }
end
_G.ShowNotification = shim.notify

function shim.draw_notifications()
    local t_now = now_ms()
    local i, y = 1, 0.72
    while i <= #notifications do
        local n = notifications[i]
        if t_now > n.until_ms then
            table.remove(notifications, i)
        else
            shim.draw_text(0.035, y, n.msg)
            y = y + 0.048
            i = i + 1
        end
    end
end

-- ===================================================================
-- 8. json (only if the runtime has none)
-- ===================================================================
if type(_G.json) ~= "table" then
    local J = {}
    local function esc(s)
        return (s:gsub('[%c"\\]', function(c)
            local m = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n',
                        ['\r'] = '\\r', ['\t'] = '\\t' }
            return m[c] or string.format("\\u%04x", c:byte())
        end))
    end
    local function enc(v)
        local t = type(v)
        if v == nil then return "null"
        elseif t == "boolean" then return tostring(v)
        elseif t == "number" then return string.format("%.14g", v)
        elseif t == "string" then return '"' .. esc(v) .. '"'
        elseif t == "table" then
            local is_arr, n = true, 0
            for k in pairs(v) do
                n = n + 1
                if type(k) ~= "number" then is_arr = false end
            end
            local out = {}
            if is_arr and n == #v then
                for _, item in ipairs(v) do out[#out + 1] = enc(item) end
                return "[" .. table.concat(out, ",") .. "]"
            end
            for k, item in pairs(v) do
                out[#out + 1] = '"' .. esc(tostring(k)) .. '":' .. enc(item)
            end
            return "{" .. table.concat(out, ",") .. "}"
        end
        return "null"
    end
    J.encode = enc
    -- Minimal recursive-descent decoder; adequate for config blobs.
    function J.decode(s)
        local pos = 1
        local function skip() pos = s:find("[^ \t\r\n]", pos) or #s + 1 end
        local parse
        local function pstr()
            pos = pos + 1
            local out = {}
            while true do
                local c = s:sub(pos, pos)
                if c == '"' then pos = pos + 1; break end
                if c == "\\" then
                    local n = s:sub(pos + 1, pos + 1)
                    local m = { n = "\n", t = "\t", r = "\r", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
                    out[#out + 1] = m[n] or n
                    pos = pos + 2
                else
                    if c == "" then break end
                    out[#out + 1] = c
                    pos = pos + 1
                end
            end
            return table.concat(out)
        end
        parse = function()
            skip()
            local c = s:sub(pos, pos)
            if c == "{" then
                pos = pos + 1
                local o = {}
                skip()
                if s:sub(pos, pos) == "}" then pos = pos + 1 return o end
                while true do
                    skip()
                    local k = pstr()
                    skip(); pos = pos + 1          -- ':'
                    o[k] = parse()
                    skip()
                    local d = s:sub(pos, pos); pos = pos + 1
                    if d == "}" then break end
                end
                return o
            elseif c == "[" then
                pos = pos + 1
                local a = {}
                skip()
                if s:sub(pos, pos) == "]" then pos = pos + 1 return a end
                while true do
                    a[#a + 1] = parse()
                    skip()
                    local d = s:sub(pos, pos); pos = pos + 1
                    if d == "]" then break end
                end
                return a
            elseif c == '"' then
                return pstr()
            else
                local lit = s:match("^[%-%w%.%+eE]+", pos)
                if lit then
                    pos = pos + #lit
                    if lit == "true" then return true end
                    if lit == "false" then return false end
                    if lit == "null" then return nil end
                    return tonumber(lit)
                end
            end
        end
        local ok, res = pcall(parse)
        return ok and res or nil
    end
    _G.json = J
end

print("[fivem2sp] shim loaded (runtime: " .. shim.runtime .. ")")
return shim
