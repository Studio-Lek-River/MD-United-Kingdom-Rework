# Millennium Dawn: United Kingdom Rework

Submod for [Millennium Dawn](https://github.com/MillenniumDawn/Millennium-Dawn) that expands the
United Kingdom (ENG) focus tree.

## How it works

Millennium Dawn keeps all ENG content in per-country files. This repo ships those same files at the
same relative paths, and a mod loaded after Millennium Dawn replaces them 1:1. Nothing else in
Millennium Dawn is touched. The full list of owned paths is `ENG_PATHS` in
[tools/sync_md_base.py](tools/sync_md_base.py).

## Install (development)

1. Clone this repo into `Documents/Paradox Interactive/Hearts of Iron IV/mod/MD-United-Kingdom-Rework`.
2. Create `mod/MD-United-Kingdom-Rework.mod` next to it with the contents of `descriptor.mod` plus
   `path="<absolute path to the clone>"`.
3. In the launcher, add it to a playset together with Millennium Dawn and place it **below** MD.

## Branches

- `md-base`: pristine copies of the ENG files from a Millennium Dawn commit. Never edit by hand.
- `main`: `md-base` plus the rework and repo scaffolding. All work happens here or on branches off it.

## Pulling in Millennium Dawn updates

```
python tools/sync_md_base.py --md <path to a Millennium Dawn checkout>
```

The script refreshes `md-base` from that checkout, commits with the MD hash, and merges `md-base`
into `main`. Files you did not change merge clean; your reworked files get normal git conflicts to
resolve.

Base: Millennium Dawn `533ffcee4e` (development branch, ahead of the current Steam release).
