# Seamless Branching helper (`service.p3i.sb`)

Some seamless-branching Blu-ray remuxes drop audio on the CoreELEC build
unless the LAV filter is put into its seamless-branching mode. This service
does that automatically: when a known SB title starts, it switches
`coreelec.amlogic.dolbyvision.audio.seamlessbranch` to the configured mode,
and restores the previous value when playback stops.

It defers to PlexMod4Kodi (`script.plexmod`) while that is running, since PM4K
applies the same workaround for Plex-sourced playback.

## When it engages

A title triggers a switch in either of two ways:

1. **Curated list.** The movie's IMDb or TMDB id is in the bundled SB list,
   **and** its audio codec is TrueHD or (E)AC3 (Atmos/JOC variants included —
   the codec name is prefix-matched, so `truehd_atmos`, `eac3_joc`, etc. all
   qualify).
2. **`SB` / `SB.txt` marker file.** A file named `SB` or `SB.txt` in the same
   folder as the playing file force-engages the helper, **bypassing the codec
   gate** — if you put the marker there, it switches. Use this when metadata is
   missing/unscraped or the title isn't on the list yet.

If LAV is already in an active SB mode (`4` or `5`) when playback starts, the
helper leaves it alone and restores nothing.

## The marker file

| Marker contents | Behaviour |
| --- | --- |
| empty | engage for **every** file in the folder (original behaviour) |
| one or more lines | engage **only** for files whose basename matches a listed entry |

Lines may be plain filenames or `fnmatch` globs, one per line; `#` and `;`
start full-line comments. Useful for flat libraries where several titles share
a folder and only some need SB.

```text
# /Movies/SB.txt
The.Tree.of.Life.2011*.mkv
Tinker.Tailor*.mkv
*Remux*1080p*          ; glob also works
```

## Settings

| Setting | Default | Notes |
| --- | --- | --- |
| Auto-enable LAV seamless-branching mode | on | Master switch for the curated-list path. The marker file still works with this off. |
| LAV mode | LAV SB | Value written when an SB title is detected: Off / Seek sync / Debug / **LAV SB** / LAV full. |
| Show notification when LAV mode is switched | on | Brief toast (5 s, so it survives the HDMI mode switch) confirming the helper engaged. |
