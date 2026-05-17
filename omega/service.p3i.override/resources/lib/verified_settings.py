# coding=utf-8
"""
Catalog of Kodi settings that have been explicitly verified to take effect
mid-playback when written via override.ini.

A setting is "verified" when:
- The C++ side reacts to mid-playback writes (OnSettingChanged callback +
  atomic-cached value, or live re-push to sysfs), AND
- It's been tested in this project.

Settings not in this table can still be written via override.ini — the
addon emits a warning but writes them anyway. Whether they take effect
mid-playback depends on whether the C++ consumer caches the value at
codec/stream open. The :status: field documents what we know:

  "live"           — OnSettingChanged + atomic, value picked up per-packet
                     or per-frame. Late writes from onAVStarted are fine.
  "live-via-sysfs" — Setting drives a sysfs flag; the change handler
                     re-pushes the sysfs on every write. Live after the
                     corresponding C++ patch lands.
  "lav-class"      — Sampled once at codec/stream open and cached. Needs a
                     C++ patch (see xbmc commit 72daca6f5a for the LAV
                     pattern) before late writes take effect.

Keep this list in sync with SETTINGS.md and the C++ side (xbmc tree).
"""

VERIFIED = {
    # ------- DV: dynamic bitstream-converter knobs -------
    "coreelec.amlogic.dolbyvision.cmv40.append": {
        "status": "live",
        "type": "int",
        "values": "0=off, 1=CMv2.9 without L2 trims, 2=always",
        "notes": (
            "Atomic-cached in CDVDVideoCodecAmlogic; applied per-packet from "
            "AddData() via ApplyDynamicDoViSettings()."
        ),
    },
    "coreelec.amlogic.dolbyvision.level5.override": {
        "status": "live",
        "type": "string",
        "format": "top,bottom,left,right (unsigned ints in RPU active-area space) or empty",
        "notes": (
            "L5 active-area override. Substituted into doviFrame/StreamMetadata "
            "during RPU parse so the overlay-active-area calc uses these offsets "
            "instead of the stream's. NOTE: this affects Kodi-side overlay and "
            "DataCacheCore consumers only — the emitted RPU still carries the "
            "stream's original L5, so the TV's tonemapping sees the original values."
        ),
    },

    # ------- DV: L5 enable surfaces (sysfs-driven) -------
    "coreelec.amlogic.dolbyvision.level5": {
        "status": "live-via-sysfs",
        "type": "bool",
        "notes": "Master L5 enable. aml_dv_apply_l5_sysfs re-pushed on change.",
    },
    "coreelec.amlogic.dolbyvision.std.source.metadata.level5": {
        "status": "live-via-sysfs",
        "type": "bool",
        "notes": "Forward source L5 metadata to the DV pipeline. Live-via-sysfs.",
    },
    "coreelec.amlogic.dolbyvision.std.source.metadata.level5.osdst": {
        "status": "live-via-sysfs",
        "type": "bool",
        "notes": "L5 OSD-start signaling. Live-via-sysfs.",
    },
    "coreelec.amlogic.dolbyvision.level5.signal.subs": {
        "status": "live-via-sysfs",
        "type": "int",
        "notes": "L5 subtitle signaling mode. Live-via-sysfs.",
    },
    "coreelec.amlogic.dolbyvision.detect.active.area": {
        "status": "live-via-sysfs",
        "type": "bool",
        "notes": "L5 active-area auto-detect. Live-via-sysfs.",
    },

    # ------- Audio: LAV seamless-branching -------
    "coreelec.amlogic.dolbyvision.audio.seamlessbranch": {
        "status": "live",
        "type": "int",
        "values": "0=off, 1=seek-sync, 3=debug, 4=LAV SB, 5=LAV full",
        "notes": (
            "Made live by xbmc commit 72daca6f5a — re-reads on codec Open() "
            "and reacts to OnSettingChanged. NOTE: if service.p3i.sb is "
            "installed, override.ini writes to this key are skipped (SB helper "
            "owns the key)."
        ),
    },
}


def is_verified(setting_id):
    return setting_id in VERIFIED


def lookup(setting_id):
    return VERIFIED.get(setting_id)
