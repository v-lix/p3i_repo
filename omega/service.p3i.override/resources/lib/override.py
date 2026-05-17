# coding=utf-8
"""
Per-folder Kodi setting overrides for service.p3i.override.

When a video plays, this module looks for "override.ini" in the same folder
as the playing file (no parent walking — drop one override.ini per folder
that needs it, including season folders for TV).

File format
-----------
INI-style. Two kinds of sections, both optional:

  [global]
  kodi.setting.id = value
  ...

  [filename or glob]
  kodi.setting.id = value

Keys before any section header are treated as implicit [global], so a folder
with one movie can just use:

  coreelec.amlogic.dolbyvision.cmv40.append = 2

For a folder with multiple files (flat movie library, TV season folder), use
sections keyed by filename basename or fnmatch glob:

  [global]
  coreelec.amlogic.dolbyvision.cmv40.append = 2

  [Avatar (2009).mkv]
  coreelec.amlogic.dolbyvision.level5.override = 140,140,0,0

  [Avatar*.mkv]
  coreelec.amlogic.dolbyvision.cmv40.append = 1

Matching: every section whose name fnmatches the playing file's basename is
applied. Apply order is declaration order; later sections override earlier
ones for the same key. [global] is always applied first. Filename matching is
case-sensitive (Linux filesystem semantics).

Values are coerced to the setting's existing type via a Settings.GetSettingValue
probe (bool / int / float / string). Unknown setting IDs pass through as
strings; JSON-RPC validates.
"""
import configparser
import fnmatch
import io
import os

import xbmcvfs

from . import util

OVERRIDE_FILENAME = "override.ini"
GLOBAL_SECTION = "global"

# Skip folder probing for these — xbmcvfs.exists against a plugin/network
# stream URL is either expensive or undefined.
REMOTE_SCHEMES = ("http://", "https://", "plugin://", "pvr://", "plex://", "upnp://")

_BOOL_TRUE = ("true", "yes", "on", "1")
_BOOL_FALSE = ("false", "no", "off", "0")


def local_folder_and_basename(playing_file):
    """(folder, basename) for playing_file, or (None, None) for remote URLs."""
    if not playing_file:
        return None, None
    if playing_file.lower().startswith(REMOTE_SCHEMES):
        return None, None
    folder = os.path.dirname(playing_file)
    basename = os.path.basename(playing_file)
    if not folder or not basename:
        return None, None
    return folder, basename


def load_override_for(playing_file):
    """Return (merged_dict, source_path or None). Empty dict means no override
    applied to this file."""
    folder, basename = local_folder_and_basename(playing_file)
    if not folder:
        return {}, None
    path = os.path.join(folder, OVERRIDE_FILENAME)
    if not xbmcvfs.exists(path):
        return {}, None

    raw = _read_text(path)
    if raw is None:
        return {}, path

    parsed = _parse(raw, path)
    if parsed is None:
        return {}, path

    merged = _merge_for_file(parsed, basename, path)
    return merged, path


def coerce_value(setting_id, raw_value):
    """(value, ok). On ok=False the caller logs and skips — never silently
    write a wrong-type value."""
    current = util.get_kodi_setting(setting_id)
    if current is None:
        # Setting unknown to Kodi (or null) — pass through; SetSettingValue
        # will reject if the ID is bogus.
        return raw_value, True

    # bool is a subclass of int — check first.
    if isinstance(current, bool):
        s = raw_value.strip().lower()
        if s in _BOOL_TRUE:
            return True, True
        if s in _BOOL_FALSE:
            return False, True
        return None, False

    if isinstance(current, int):
        try:
            return int(raw_value), True
        except (TypeError, ValueError):
            return None, False

    if isinstance(current, float):
        try:
            return float(raw_value), True
        except (TypeError, ValueError):
            return None, False

    # Strings (including L5 override "top,bottom,left,right") pass through.
    return raw_value, True


def _read_text(path):
    f = xbmcvfs.File(path)
    try:
        data = f.read()
    finally:
        f.close()
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            util.warn("override.ini {}: not valid UTF-8, skipped".format(path))
            return None
    return data


def _ensure_global_header(raw):
    """If the first non-blank, non-comment line isn't a section header, prepend
    [global] so configparser accepts the file."""
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ";")):
            continue
        if s.startswith("["):
            return raw
        return "[{}]\n{}".format(GLOBAL_SECTION, raw)
    return raw


def _parse(raw, path):
    """Returns a list of (section_name, dict_of_keys_in_declaration_order).
    Section order matches the file; key order within a section matches the
    file. Returns None on parse error."""
    prepped = _ensure_global_header(raw)
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    # Kodi setting IDs are already lowercase, but the default optionxform
    # lowercases values' keys — preserve case so any future setting with mixed
    # case still routes correctly.
    cp.optionxform = str
    try:
        cp.read_file(io.StringIO(prepped), source=path)
    except configparser.Error as exc:
        util.warn("override.ini {}: parse error: {}".format(path, exc))
        return None

    sections = []
    for name in cp.sections():
        kv = {}
        for k in cp.options(name):
            kv[k] = cp.get(name, k)
        sections.append((name, kv))
    return sections


def _merge_for_file(sections, basename, path):
    """Apply [global] first, then each section whose name fnmatches basename,
    in declaration order. Returns {setting_id: raw_value_string}."""
    merged = {}
    for name, kv in sections:
        if name == GLOBAL_SECTION:
            merged.update(kv)
            continue
        if fnmatch.fnmatchcase(basename, name):
            merged.update(kv)
            util.debug("override.ini {}: section [{}] matched {}".format(path, name, basename))
    return merged
