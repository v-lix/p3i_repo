# coding=utf-8
import json
import os

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))

LOG_PREFIX = "service.p3i.override"

# ID of the SB helper. If it's installed, we don't touch the LAV SB setting
# from override.ini — SB helper owns that key (via curated list + marker
# logic) and racing two writers on the same setting is asking for trouble.
SB_HELPER_ADDON_ID = "service.p3i.sb"
SB_SETTING_ID = "coreelec.amlogic.dolbyvision.audio.seamlessbranch"


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[{}] {}".format(LOG_PREFIX, msg), level)


def debug(msg):
    log(msg, xbmc.LOGDEBUG)


def warn(msg):
    log(msg, xbmc.LOGWARNING)


def error(msg):
    log(msg, xbmc.LOGERROR)


def get_setting_bool(key, default=False):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        v = ADDON.getSetting(key)
        if v in ("true", "True", "1"):
            return True
        if v in ("false", "False", "0", ""):
            return False
        return default


def pm4k_running():
    """True if PlexMod4Kodi (script.plexmod) is the active session."""
    return xbmc.getInfoLabel("Window(10000).Property(script.plex.running)") == "1"


def sb_helper_installed():
    """True if service.p3i.sb is installed and enabled. Used to decide whether
    to filter the SB setting key out of override.ini applies."""
    # getCondVisibility returns truthy when the addon exists *and* is enabled,
    # which is exactly the gate we want — a disabled SB helper isn't writing
    # anything, so we don't need to skip on its behalf.
    try:
        return xbmc.getCondVisibility("System.HasAddon({})".format(SB_HELPER_ADDON_ID)) == 1
    except Exception:
        return False


def jsonrpc(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        req["params"] = params
    raw = xbmc.executeJSONRPC(json.dumps(req))
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def get_kodi_setting(setting_id):
    resp = jsonrpc("Settings.GetSettingValue", {"setting": setting_id})
    return resp.get("result", {}).get("value")


def set_kodi_setting(setting_id, value):
    resp = jsonrpc("Settings.SetSettingValue", {"setting": setting_id, "value": value})
    return resp.get("result") is True
