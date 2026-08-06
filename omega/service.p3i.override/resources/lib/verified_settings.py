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

  "live"             — OnSettingChanged + atomic, value picked up per-packet
                       or per-frame. Late writes from onAVStarted are fine.
  "live-via-sysfs"   — Setting drives a sysfs flag; the change handler
                       re-pushes the sysfs on every write. Live after the
                       corresponding C++ patch lands.
  "live-on-next-cue" — Value is cached in a render-time style struct, but
                       an observer fires on settings change and the next
                       drawn subtitle picks it up. Applies within one cue
                       (typically <1s for dense dialogue, longer for sparse
                       subs). Useful in practice; not instant.
  "live-on-seek"     — Value is applied at codec open AND on every codec
                       Reset() (seek/flush). A write from onAVStarted lands
                       on the first seek, not instantly.
  "lav-class"        — Sampled once at codec/stream open and cached. Needs a
                       C++ patch (see xbmc commit 72daca6f5a for the LAV
                       pattern) before late writes take effect.
  "needs-restart"    — Sampled at codec/stream/demuxer open or app startup
                       and never re-read. Mid-playback write may apply to
                       the next playback but not the current one. Document
                       and warn; the addon writes anyway in case the user
                       wants it set going forward.

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
            "AddData() via ApplyDynamicDoViSettings(). WRITABLE ONLY WHEN: "
            "DV type = Display-LED (0), no VP override (video.processor = 0), "
            "and DV mode != 2 — these are visible-dependencies on the setting. "
            "On other paths Kodi rejects the JSON-RPC write with InvalidParams "
            "(the addon logs this) and the codec also zeroes the value, since "
            "CMv4.0 append only matters when the TV does the tonemapping. "
            "If your override fails on a Player-LED / LLDV / VS10 setup this "
            "is the reason — set DV type to Display-LED, or scope the override "
            "to titles played in that mode."
        ),
    },
    "coreelec.amlogic.dolbyvision.level5.override": {
        "status": "live",
        "type": "string",
        "format": "top,bottom,left,right (unsigned ints in RPU active-area space) or empty",
        "notes": (
            "L5 active-area override. Both substituted into doviFrame/StreamMetadata "
            "during RPU parse (Kodi-side overlay-active-area calc) AND pushed to the "
            "amdolby_vision kernel module via xbmc_detected_l5_* + xbmc_force_l5_override "
            "sysfs (so the TV sees the override values in the outgoing RPU). "
            "Empty value = no override (stream's L5 passes through). "
            "Any successful parse counts as active, including '0,0,0,0' which is a "
            "legitimate override meaning 'treat the stream as having no bars / full "
            "active frame' — useful for fixing streams whose RPU falsely claims "
            "letterbox. When active, also stops the L5 auto-detect path (override "
            "values supplant detected values everywhere)."
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

    # ------- Audio: decode-side -------
    "audiooutput.drc": {
        "status": "live-on-seek",
        "type": "int",
        "values": "0-100 (percent; drc_scale 0.0-1.0)",
        "notes": (
            "AC3/E-AC3 dynamic range compression. Read in ApplyDrcScale(), "
            "called at codec open and on every Reset() (seek/flush) - a "
            "mid-playback write takes effect on the first seek. "
            "advancedsettings.xml <applydrc> overrides the slider when set."
        ),
    },
    "audiooutput.ignoredownmixmetadata": {
        "status": "live",
        "type": "bool",
        "notes": (
            "Read per-frame in CDVDAudioCodecFFmpeg::GetData when downmix "
            "side data is present. Per-title escape hatch for streams with "
            "broken downmix metadata."
        ),
    },

    # ------- Audio: downmix / resampler (RECONFIGURE + resampler recreate) -------
    "audiooutput.maintainoriginalvolume": {
        "status": "live",
        "type": "bool",
        "notes": (
            "Flips downmix normalization; ActiveAE RECONFIGURE recreates the "
            "resampler. Only matters when downmixing to fewer channels."
        ),
    },
    "audiooutput.boostcenter": {
        "status": "live",
        "type": "float",
        "values": "0.0 = off; dB of centre boost otherwise",
        "notes": (
            "Centre-channel boost folded into the downmix matrix. Live since "
            "the T4 ConfigureResampler change-detect patch (recreates the "
            "resampler on change); before that build it was sampled at "
            "stream open only."
        ),
    },
    "audiooutput.lfemixto": {
        "status": "live",
        "type": "int",
        "values": "0=LFE dropped/default, 1=redirect LFE to front L/R",
        "notes": (
            "LFE downmix routing; needs audiooutput.mixsublevel > 0 to have "
            "any effect. Live since the T4 ConfigureResampler change-detect "
            "patch."
        ),
    },
    "audiooutput.mixsublevel": {
        "status": "live",
        "type": "int",
        "values": "0-100 (percent LFE level in downmix)",
        "notes": "LFE level in the downmix matrix. Live since the T4 ConfigureResampler change-detect patch.",
    },
    "audiooutput.stereoupmix": {
        "status": "live",
        "type": "bool",
        "notes": (
            "2.0 -> multichannel upmix. Live since the T4 ConfigureResampler "
            "change-detect patch. Visible-dependency: only writable when the "
            "sink offers >2 channels."
        ),
    },

    # ------- Audio: passthrough codec toggles (live codec re-selection) -------
    # All of these are made live by the T4 VideoPlayerAudio settings-callback
    # patch: a change flags the player thread, which re-runs
    # SwitchCodecIfNeeded() with live setting reads (SupportsRaw). Expect a
    # short audio drop while the codec switches.
    # VISIBILITY: all format toggles are dependency-hidden unless master
    # audiooutput.passthrough is enabled AND the passthrough device supports
    # the format - writes to hidden settings fail with InvalidParams (logged).
    "audiooutput.ac3passthrough": {
        "status": "live",
        "type": "bool",
        "notes": "Live codec re-selection via SwitchCodecIfNeeded.",
    },
    "audiooutput.eac3passthrough": {
        "status": "live",
        "type": "bool",
        "notes": "Live codec re-selection via SwitchCodecIfNeeded.",
    },
    "audiooutput.dtspassthrough": {
        "status": "live",
        "type": "bool",
        "notes": "Covers plain DTS and the DTS-HD core fallback path.",
    },
    "audiooutput.dtshdpassthrough": {
        "status": "live",
        "type": "bool",
        "notes": (
            "DTS-HD HRA/MA passthrough. Per-title 'core only for this one' "
            "combos with audiooutput.dtshdcorefallback."
        ),
    },
    "audiooutput.truehdpassthrough": {
        "status": "live",
        "type": "bool",
        "notes": (
            "Per-title 'decode TrueHD instead of bitstreaming' - e.g. for "
            "titles whose TrueHD passthrough overloads the receiver."
        ),
    },
    "audiooutput.ac3transcode": {
        "status": "live",
        "type": "bool",
        "notes": (
            "Transcode multichannel PCM to AC3. Codec choice reacts live; "
            "the AE-side transcode decision lands with the engine "
            "RECONFIGURE a moment later."
        ),
    },
    "audiooutput.dtshdcorefallback": {
        "status": "live",
        "type": "bool",
        "notes": (
            "Fall back to the DTS core when DTS-HD passthrough is off/"
            "unsupported. VISIBILITY: dependency-hidden unless "
            "audiooutput.dtshdpassthrough is FALSE - write that one first "
            "in the same override.ini if you need both."
        ),
    },

    # ------- Subtitles: PGS HDR-to-SDR shader params (per-frame live) -------
    "subtitles.pgshdrtosdr.brightness": {
        "status": "live",
        "notes": "Fed per-frame to the PGS HDR-to-SDR shader as m_pqRefNits.",
    },
    "subtitles.pgshdrtosdr.saturation": {
        "status": "live",
        "notes": "Fed per-frame to the PGS HDR-to-SDR shader as m_pqSaturation.",
    },
    "subtitles.pgshdrtosdr.tonemap": {
        "status": "live",
        "notes": "Per-frame: selects the shader tone-mapping pipeline.",
    },
    "subtitles.pgshdrtosdr.mode": {
        "status": "live",
        "values": "Classic / Linear / Luma (see memory pgs-hdr-color-fix)",
        "notes": "Per-frame: selects the tonemapping algorithm in the shader.",
    },

    # ------- Subtitles: other render-time live settings -------
    "subtitles.captionsalign": {
        "status": "live",
        "notes": "Read per-frame in ConvertLibass via rOpts.horizontalAlignment.",
    },
    "subtitles.stereoscopicdepth": {
        "status": "live",
        "notes": "Read per-frame in GetStereoscopicDepth() for the 3D offset.",
    },
    "subtitles.bitmapzoom": {
        "status": "live",
        "notes": "Read per-frame for bitmap scale + GPU texture filter.",
    },

    # ------- Subtitles: style (cached in m_overlayStyle, applies on next cue) -------
    "subtitles.fontname": {
        "status": "live-on-next-cue",
        "notes": "Baked into ASS style at first render; SubtitlesSettings observer triggers re-cache so the next drawn subtitle picks it up.",
    },
    "subtitles.fontsize": {
        "status": "live-on-next-cue",
        "notes": "Baked into ASS style with playResY scaling. Observer-refreshed.",
    },
    "subtitles.style": {
        "status": "live-on-next-cue",
        "notes": "Font bold/italic. Observer-refreshed.",
    },
    "subtitles.colorpick": {
        "status": "live-on-next-cue",
        "notes": "Font colour. Observer-refreshed; applies on next subtitle cue.",
    },
    "subtitles.bordersize": {
        "status": "live-on-next-cue",
        "notes": "ASS Outline. Observer-refreshed.",
    },
    "subtitles.bordercolorpick": {
        "status": "live-on-next-cue",
        "notes": "ASS OutlineColour. Observer-refreshed.",
    },
    "subtitles.opacity": {
        "status": "live-on-next-cue",
        "notes": "Font opacity. Observer-refreshed.",
    },
    "subtitles.blur": {
        "status": "live-on-next-cue",
        "notes": "Blur. Observer-refreshed.",
    },
    "subtitles.backgroundtype": {
        "status": "live-on-next-cue",
        "notes": "ASS borderStyle (outline / box). Observer-refreshed.",
    },
    "subtitles.shadowcolor": {
        "status": "live-on-next-cue",
        "notes": "ASS BackColour (shadow). Observer-refreshed.",
    },
    "subtitles.shadowopacity": {
        "status": "live-on-next-cue",
        "notes": "Shadow opacity. Observer-refreshed.",
    },
    "subtitles.shadowsize": {
        "status": "live-on-next-cue",
        "notes": "ASS Shadow. Observer-refreshed.",
    },
    "subtitles.bgcolorpick": {
        "status": "live-on-next-cue",
        "notes": "Background colour. Observer-refreshed.",
    },
    "subtitles.bgopacity": {
        "status": "live-on-next-cue",
        "notes": "Background opacity. Observer-refreshed.",
    },
    "subtitles.marginvertical": {
        "status": "live-on-next-cue",
        "notes": (
            "Vertical margin. Observer-refreshed. NOTE: source-level comment "
            "warns that mid-playback changes cause seek artifacts — prefer "
            "setting at start of playback rather than toggling during."
        ),
    },
    "subtitles.align": {
        "status": "live-on-next-cue",
        "notes": "ASS alignment. Observer-refreshed.",
    },
    "subtitles.overridefonts": {
        "status": "live-on-next-cue",
        "notes": "Whether to override ASS-embedded fonts. Observer-refreshed.",
    },
    "subtitles.overridestyles": {
        "status": "live-on-next-cue",
        "notes": "Override ASS style enum. Observer-refreshed.",
    },
    "subtitles.overrideass": {
        "status": "live-on-next-cue",
        "notes": "Whether to apply override flags. Observer-refreshed.",
    },

    # ------- Subtitles: needs-restart (sampled at stream/codec open) -------
    "subtitles.pgshdrtosdr": {
        "status": "needs-restart",
        "notes": (
            "Master PGS HDR-to-SDR enable. Sampled at PGS codec open in "
            "DVDOverlayCodecFFmpeg; mid-playback toggle won't reopen. Set "
            "globally; tune the brightness/saturation/tonemap/mode params "
            "per folder instead."
        ),
    },
    "subtitles.charset": {
        "status": "needs-restart",
        "notes": "Applied to libass at subtitle-stream Configure(); mid-playback change won't reconfigure.",
    },
    "subtitles.parsecaptions": {
        "status": "needs-restart",
        "notes": "Sampled during demux setup. Mid-playback toggle won't take effect.",
    },
    "locale.subtitlelanguage": {
        "status": "needs-restart",
        "notes": "Read at subtitle-stream selection time. Mid-playback change won't reselect the active subtitle track.",
    },
}


def is_verified(setting_id):
    return setting_id in VERIFIED


def lookup(setting_id):
    return VERIFIED.get(setting_id)
