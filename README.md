# Millennium Dawn: United Kingdom Rework

Submod for [Millennium Dawn](https://github.com/MillenniumDawn/Millennium-Dawn) that expands the
United Kingdom (ENG) focus tree.

## Validation

Pull requests run Millennium Dawn's validator suite against this repo's files overlaid on MD at the
commit in `tools/md_base_ref.txt`. Run it locally with `python tools/validate_with_md.py` (needs an
MD checkout that contains that commit, default `D:/Documenten/Paradox Interactive/Hearts of Iron IV/mod/Millennium-Dawn`).

## Versioning

`descriptor.mod` holds the submod version (`MAJOR.MINOR.PATCH`: PATCH for fixes, MINOR for new
content, MAJOR for save-breaking changes). Bump it on every upload. `Changelog.txt` records each
version and the Millennium Dawn release it targets.

## Publishing to Steam Workshop

1. Run `python tools/build_workshop.py`. It stages only the game files in
   `../MD-United-Kingdom-Rework-Workshop` and writes the matching `.mod` launcher file.
2. In the Paradox launcher, open Mod Tools > Upload Mod and pick that mod.
3. On the Workshop page, add Millennium Dawn as a Required Item. Steam does not read
   `dependencies` from the descriptor.
4. After the first upload, copy the `remote_file_id` the launcher added into this repo's
   `descriptor.mod` so later builds update the same Workshop item.

## After a Millennium Dawn update

The submod replaces whole MD files, so MD fixes to those files stay hidden until you re-sync.

1. In the MD checkout: `git fetch --tags` and check out the new release tag.
2. Run `python tools/sync_md_base.py` and resolve the merge.
3. Run `python tools/validate_with_md.py --ref <tag>`.
4. Bump the version, add a `Changelog.txt` entry, rebuild, and upload.
