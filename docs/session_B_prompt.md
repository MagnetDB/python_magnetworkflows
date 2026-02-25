# Session B — Apply patches to python_magnetcooling submodule

## Context

This is **Session B** of the migration of cooling physics from `python_magnetworkflows`
to the `python_magnetcooling` submodule.

**Session A** (COMPLETE): patch files were created and committed to the
`python_magnetworkflows` repository at `docs/patches/0001`–`0006`.

**Your task (Session B):** apply those patches to the `python_magnetcooling` submodule,
commit, push, and update the submodule pointer in `python_magnetworkflows`.

**Reference:** `docs/migration_magnetcooling.md` §2–§3 (full migration guide in this repo).

---

## Repository / Branch

| Repo | Branch |
|------|--------|
| `python_magnetworkflows` | `claude/integrate-magnetcooling-package-PlVOL` |
| `python_magnetcooling` (submodule) | create or use a feature branch, e.g. `fix/feelpp-integration-patches` |

---

## Submodule State

The submodule is declared in `.gitmodules` at path `python_magnetcooling` pointing to
`git@github.com:MagnetDB/python_magnetcooling.git`.

The current pinned commit is `a95e1d18c865841df0acc2d9446f35ec30374ad5`.

The patches in `docs/patches/` were generated against **exactly this commit**.

---

## Step-by-Step Instructions

### 1. Verify you are on the correct python_magnetworkflows branch

```bash
cd /path/to/python_magnetworkflows
git status          # should be on claude/integrate-magnetcooling-package-PlVOL
git log --oneline -5
```

### 2. Initialise and update the submodule

```bash
git submodule update --init python_magnetcooling
```

Confirm the checked-out commit matches the pinned one:

```bash
cd python_magnetcooling
git log --oneline -3
# Expected HEAD: a95e1d1  (or however the commit is abbreviated)
```

### 3. Create a feature branch in the submodule

```bash
git checkout -b fix/feelpp-integration-patches
```

### 4. Apply patches in order

```bash
cd /path/to/python_magnetworkflows
for p in docs/patches/0*.patch; do
    echo "==> Applying $p"
    git -C python_magnetcooling apply --ignore-whitespace "$p" && echo "OK"
done
```

If a patch fails to apply cleanly:

```bash
git -C python_magnetcooling apply --reject --ignore-whitespace docs/patches/<failing>.patch
# Edit the *.rej files manually, then:
git -C python_magnetcooling add python_magnetcooling/feelpp.py
```

### 5. Verify the patched file

```bash
cd python_magnetcooling
git diff
```

Confirm the following changes are present in `python_magnetcooling/feelpp.py`:

| Patch | Location | Change |
|-------|----------|--------|
| 0001 | line ~78 | `dpressure()` → `pressure_drop()` |
| 0002 | line ~110 | `TwH[i]["value"]` → read Tw from CSV |
| 0003 | line ~93 | guard against empty `dTwH` |
| 0004 | line ~167 | `targets[target]["pextra"]` → `.get("pextra", 1)` |
| 0005 | line ~265 | channel name from `p_params["Dh"][i]` |
| 0006 | lines ~57,193,240 | CSV write-back for gradHZ/gradHZH + `_extract_parameter_updates` signature |

### 6. Run submodule tests (if any)

```bash
cd python_magnetcooling
pytest tests/ -v   # skip if no tests yet
```

### 7. Commit and push the submodule

```bash
cd python_magnetcooling
git commit -am "fix: apply python_magnetworkflows integration patches

Fixes 6 bugs in feelpp.py required for integration with python_magnetworkflows:
  - pressure_drop method name
  - TwH dict inlet temperature from CSV
  - empty dTwH guard
  - pextra optional key
  - channel name from p_params
  - axial CSV write-back for gradHZ/gradHZH modes"
git push -u origin fix/feelpp-integration-patches
```

### 8. Update the submodule pointer in python_magnetworkflows

```bash
cd /path/to/python_magnetworkflows
git add python_magnetcooling
git commit -m "chore: update python_magnetcooling submodule to patched commit"
git push -u origin claude/integrate-magnetcooling-package-PlVOL
```

### 9. Open a pull request in python_magnetcooling (optional)

If the project requires PR review before merging to main:

```bash
gh pr create \
  --repo MagnetDB/python_magnetcooling \
  --head fix/feelpp-integration-patches \
  --base main \
  --title "fix: feelpp.py integration patches for python_magnetworkflows" \
  --body "Fixes 6 bugs required for the python_magnetworkflows integration.
See python_magnetworkflows docs/patches/README.md for details."
```

---

## Verification After Session B

The following should all pass before starting Session C:

```bash
cd python_magnetcooling
python -c "from python_magnetcooling.feelpp import FeelppThermalHydraulicAdapter; print('OK')"
python -c "from python_magnetcooling.thermohydraulics import ThermalHydraulicCalculator; print('OK')"
python -c "from python_magnetcooling import WaterFlow; print('OK')"
python -c "from python_magnetcooling.cooling import steam; print('OK')"
```

---

## Files to Reference

- `docs/patches/README.md` — how-to-apply guide
- `docs/patches/0001`–`0006` — the patch files
- `docs/migration_magnetcooling.md` §3 — description of each bug
- `docs/session_C_prompt.md` — next session prompt
