# python_magnetcooling Integration Patches

These patches fix 6 issues in `python_magnetcooling` required for the
integration with `python_magnetworkflows`.  They were created against commit
`a95e1d18c865841df0acc2d9446f35ec30374ad5` of the submodule.

## How to apply

```bash
# 1. Initialise the submodule (from python_magnetworkflows root)
git submodule update --init python_magnetcooling
cd python_magnetcooling

# 2. Apply all patches in order
for p in ../docs/patches/0*.patch; do
    echo "==> $p"
    git apply --ignore-whitespace "$p" && echo "OK"
done

# 3. Commit and push in the submodule
git commit -am "fix: apply python_magnetworkflows integration patches"
git push

# 4. Update the submodule reference in python_magnetworkflows
cd ..
git add python_magnetcooling
git commit -m "chore: update python_magnetcooling to patched commit"
```

If a patch fails to apply cleanly, use:

```bash
git apply --reject --ignore-whitespace <patch_file>
# then manually resolve *.rej files
```

## Patch summary

| File | Patch | Bug description |
|------|-------|-----------------|
| `0001` | feelpp.py line 78 | `waterflow.dpressure()` → `waterflow.pressure_drop()` |
| `0002` | feelpp.py line 110 | TwH[i] dict: read inlet Tw from CSV, not `TwH[i]["value"]` |
| `0003` | feelpp.py line 93 | Empty `dTwH` list must default to zeros |
| `0004` | feelpp.py line 167 | `targets[target]["pextra"]` → `.get("pextra", 1)` |
| `0005` | feelpp.py line 265 | Channel name via p_params, not `channel_out.geometry.name` |
| `0006` | feelpp.py lines 57,193,240 | Add CSV write-back for axial modes (gradHZ/gradHZH) |
