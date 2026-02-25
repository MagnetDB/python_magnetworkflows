# Session C — Update python_magnetworkflows to use python_magnetcooling

## Context

This is **Session C** of the migration of cooling physics from `python_magnetworkflows`
to the `python_magnetcooling` submodule.

**Session A** (COMPLETE): patch files created in `docs/patches/`.
**Session B** (COMPLETE): patches applied to `python_magnetcooling`, submodule pointer updated.

**Your task (Session C):** update `error.py` and `cli.py` to delegate to the adapter,
remove the now-redundant local modules `cooling.py` and `waterflow.py`, and verify.

**Reference:** `docs/migration_magnetcooling.md` §4–§9 (full migration guide in this repo).

---

## Repository / Branch

| Repo | Branch |
|------|--------|
| `python_magnetworkflows` | `claude/integrate-magnetcooling-package-PlVOL` |

---

## Prerequisites

Before starting, confirm:

```bash
# 1. Submodule is initialised and at the patched commit
git submodule status python_magnetcooling   # should show a commit hash

# 2. python_magnetcooling package is importable
python -c "from python_magnetcooling.feelpp import FeelppThermalHydraulicAdapter; print('OK')"
python -c "from python_magnetcooling import WaterFlow; print('OK')"

# 3. (If not installed yet)
pip install -e python_magnetcooling/
```

---

## Step-by-Step Instructions

### 1. Create backup copies of the local modules

```bash
cp python_magnetworkflows/python_magnetworkflows/cooling.py \
   python_magnetworkflows/python_magnetworkflows/cooling.py.bak
cp python_magnetworkflows/python_magnetworkflows/waterflow.py \
   python_magnetworkflows/python_magnetworkflows/waterflow.py.bak
git add python_magnetworkflows/python_magnetworkflows/cooling.py.bak \
        python_magnetworkflows/python_magnetworkflows/waterflow.py.bak
```

### 2. Update `error.py`

File: `python_magnetworkflows/python_magnetworkflows/error.py`

#### 2a. Replace the import block (top of file, ~lines 3–5)

```python
# REMOVE:
from .waterflow import waterflow as w
from .cooling import steam, Uw, getDT, getHeatCoeff, getTout

# ADD:
from python_magnetcooling.feelpp import FeelppThermalHydraulicAdapter
from python_magnetcooling.thermohydraulics import (
    ThermalHydraulicCalculator,
    compute_mixed_outlet_temperature,
)
from python_magnetcooling.cooling import steam  # used only for site-level mixing
```

#### 2b. Replace the cooling update block (lines 434–828)

The block starts with `if args.update_cooling:` and ends just before
`err_max_dT = max(...)`.  Keep the `if args.update_cooling:` guard.

Replace the body of the block with:

```python
        if args.update_cooling:
            flow = values["waterflow"]
            Pressure = flow.pressure(abs(objectif))
            dict_df[target]["flow"] = flow.flow_rate(abs(objectif))

            # Delegate all thermal-hydraulic computation to python_magnetcooling
            _adapter = FeelppThermalHydraulicAdapter(ThermalHydraulicCalculator())
            th_output, param_updates, dict_df_update = _adapter.compute_from_feelpp_data(
                target, dict_df, p_params, parameters, targets, args, basedir
            )

            # Apply outer-iteration relaxation before storing to parameters
            relax = float(values["relax"])
            for param_name, new_value in param_updates.items():
                old_value = parameters.get(param_name, new_value)
                parameters[param_name] = (1.0 - relax) * new_value + relax * old_value

            # Merge thermal-hydraulic results into dict_df
            dict_df[target].update(dict_df_update.get(target, {}))

            # Track convergence errors for outer loop
            err_max_dT = max(err_max_dT, th_output.max_error_temp)
            err_max_h = max(err_max_h, th_output.max_error_heat_coeff)

            print(
                f"{target} cooling={args.cooling}: it={it} "
                f"err_max_dT={err_max_dT:.3e}, err_max_h={err_max_h:.3e}",
                flush=True,
            )

            # Accumulate per-target outlet data for multi-magnet site mixing
            Tout = th_output.outlet_temp_mixed
            _steam = steam(Tout, Pressure)
            List_Tout.append(Tout)
            List_VolMassout.append(_steam.rho)
            List_SpecHeatout.append(_steam.cp * 1.0e3)
            List_Qout.append(th_output.total_flow_rate)
            del _steam
```

#### 2c. Replace `getTout` call for site-level mixing (~line 830)

```python
# REMOVE:
Tout_site = getTout(List_Tout, List_VolMassout, List_SpecHeatout, List_Qout)

# ADD:
Tout_site = compute_mixed_outlet_temperature(
    List_Tout, List_VolMassout, List_SpecHeatout, List_Qout
)
```

#### Relaxation semantics note

The adapter is called with `relaxation_factor=0.0` (default in `ThermalHydraulicInput`)
to avoid internal relaxation.  The explicit blend above preserves the original
outer-iteration relaxation behaviour exactly.

---

### 3. Update `cli.py`

File: `python_magnetworkflows/python_magnetworkflows/cli.py`

#### 3a. Replace import block (~lines 18–19)

```python
# REMOVE:
from .waterflow import waterflow
from .cooling import getDT, getHeatCoeff

# ADD:
from python_magnetcooling import WaterFlow
from python_magnetcooling.cooling import getDT, getHeatCoeff
```

`getDT` and `getHeatCoeff` are stored as callable references in heat-param config dicts
(lines ~356, ~367, ~381, ~392).  The function signatures are identical; no other changes
needed.

#### 3b. Replace waterflow instantiation in `configure_magnet_target` (~line 588)

```python
# REMOVE:
"waterflow": waterflow.flow_params(
    values["flow"]
    if os.path.isabs(values["flow"])
    else os.path.join(pwd, values["flow"])
),

# ADD:
"waterflow": WaterFlow.from_file(
    values["flow"]
    if os.path.isabs(values["flow"])
    else os.path.join(pwd, values["flow"])
),
```

---

### 4. Remove local modules

```bash
git rm python_magnetworkflows/python_magnetworkflows/cooling.py
git rm python_magnetworkflows/python_magnetworkflows/waterflow.py
```

---

### 5. Update `pyproject.toml`

Add `python-magnetcooling` to the project dependencies:

```toml
[project]
dependencies = [
    # … existing deps …
    "python-magnetcooling",
]
```

---

### 6. Verification

```bash
# Import checks
python -c "from python_magnetworkflows.error import compute_error; print('error: OK')"
python -c "from python_magnetworkflows.cli import main; print('cli: OK')"

# Confirm old modules are gone
python -c "from python_magnetworkflows.cooling import getDT" 2>&1   # expect ImportError
python -c "from python_magnetworkflows.waterflow import waterflow" 2>&1  # expect ImportError

# Run existing tests (if any)
pytest tests/ -v

# Smoke test (noupdate skips the cooling solver, just checks imports + config parsing)
python_magnetworkflows <cfgfile> \
  --mdata '{"M9":{"type":"helix","value":31000,"flow":"flow.json"}}' \
  --cooling mean --noupdate
```

---

### 7. Commit and push

```bash
git add python_magnetworkflows/python_magnetworkflows/error.py \
        python_magnetworkflows/python_magnetworkflows/cli.py \
        python_magnetworkflows/python_magnetworkflows/cooling.py.bak \
        python_magnetworkflows/python_magnetworkflows/waterflow.py.bak \
        pyproject.toml
git commit -m "feat: delegate cooling to python_magnetcooling adapter

Replace ~400 lines of local cooling logic in error.py with calls to
FeelppThermalHydraulicAdapter.  Update cli.py to use WaterFlow.from_file().
Remove cooling.py and waterflow.py (backups kept as *.bak).

Closes #<issue> if applicable."
git push -u origin claude/integrate-magnetcooling-package-PlVOL
```

---

## API Mapping Reference

| Old (`python_magnetworkflows`) | New (`python_magnetcooling`) |
|---|---|
| `waterflow.flow_params(filename)` | `WaterFlow.from_file(filename)` |
| `w.flow(current)` | `w.flow_rate(current)` |
| `w.pressure(current)` | `w.pressure(current)` *(unchanged)* |
| `w.dpressure(current)` | `w.pressure_drop(current)` |
| `w.umean(current, section)` | `w.velocity(current, section)` |
| `getTout(...)` | `compute_mixed_outlet_temperature(...)` |

---

## Files to Reference

- `docs/migration_magnetcooling.md` §4–§9 — detailed change descriptions with line numbers
- `docs/session_B_prompt.md` — previous session (apply patches)
- `python_magnetworkflows/error.py` — main file to edit (842 lines as of start)
- `python_magnetworkflows/cli.py` — secondary file to edit (1120 lines as of start)
