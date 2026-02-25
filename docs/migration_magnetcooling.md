# Migrating Cooling Physics to python_magnetcooling

**Branch:** `claude/integrate-magnetcooling-package-PlVOL`
**Goal:** Remove `cooling.py` and `waterflow.py` from `python_magnetworkflows` and delegate all cooling-related computation to the `python_magnetcooling` submodule via its `feelpp.py` adapter.

---

## 1. Overview

`python_magnetworkflows` currently duplicates cooling physics in two local modules:

| Local file | What it contains |
|---|---|
| `python_magnetworkflows/cooling.py` | Water properties (`steam`), heat correlations (Montgomery/Dittus/…), friction models, `Uw`, `getDT`, `getHeatCoeff`, `getTout` |
| `python_magnetworkflows/waterflow.py` | Pump model (`waterflow` dataclass): `flow_params`, `flow`, `pressure`, `dpressure`, `umean` |

Both are superseded by `python_magnetcooling`:

| python_magnetcooling module | Replaces |
|---|---|
| `python_magnetcooling/cooling.py` | Local `cooling.py` (same functions, same signatures) |
| `python_magnetcooling/waterflow.py` | Local `waterflow.py` (same logic, renamed methods — see §4) |
| `python_magnetcooling/thermohydraulics.py` | The ~400-line cooling block in `error.py` |
| `python_magnetcooling/feelpp.py` | The adapter that ties them all together |

---

## 2. Session-by-Session Plan

### Session A — Fix python_magnetcooling bugs
*Prerequisite: submodule initialized + submodule repo editable*

1. Initialize the submodule:
   ```bash
   git submodule update --init python_magnetcooling
   ```
2. Apply the 6 bug-fixes described in §3 to `python_magnetcooling/feelpp.py`
3. Add `name: str = ""` field to `ChannelOutput` and propagate it (see §3.0)
4. Commit changes inside the submodule, push to `MagnetDB/python_magnetcooling`
5. Update the submodule reference in python_magnetworkflows: `git add python_magnetcooling && git commit`

### Session B — Update python_magnetworkflows
*Prerequisite: Session A complete, submodule at fixed commit, package installed*

1. Install package: `pip install -e python_magnetcooling/`
2. Create backup copies of local modules (§5)
3. Update `error.py` (§6)
4. Update `cli.py` (§7)
5. Remove `cooling.py` and `waterflow.py` with `git rm`
6. Run verification checks (§8)
7. Commit + push to `claude/integrate-magnetcooling-package-PlVOL`

---

## 3. Bugs to Fix in python_magnetcooling

These must all be applied during Session A before python_magnetworkflows can use the adapter.

### 3.0  `channel.py` or `thermohydraulics.py` — add `name` to `ChannelOutput`

`ChannelOutput` is a dataclass without a `name` field, but `_update_dict_df` in `feelpp.py` needs to know the channel name. Two-part fix:

**Part A** — Add field to `ChannelOutput` (in `channel.py` or wherever `ChannelOutput` is defined):
```python
@dataclass
class ChannelOutput:
    name: str = ""          # <-- add this line
    velocity: float
    # … rest of fields unchanged
```

**Part B** — Populate it in `ThermalHydraulicCalculator.compute()` (in `thermohydraulics.py`), after creating each `ChannelOutput`:
```python
output.name = channel.geometry.name
```
(add immediately after `output = self._compute_channel_uniform(channel, inputs)` or `_compute_channel_axial`)

---

### 3.1  `feelpp.py` — Bug 1: wrong `WaterFlow` method name

`WaterFlow` (python_magnetcooling) has `pressure_drop()`, not `dpressure()`.

**Location:** `_build_input_from_feelpp`, near top of method.

```diff
- dpressure = waterflow.dpressure(objectif)
+ dpressure = waterflow.pressure_drop(objectif)
```

---

### 3.2  `feelpp.py` — Bug 2: wrong key when TwH[i] is a dict

When `TwH[i]` is a dict it has a `"filename"` key (path to CSV), **not** a `"value"` key. The inlet temperature must be read from the CSV's first row.

**Location:** `_build_input_from_feelpp`, channel-loop body.

```diff
- Tw_inlet = TwH[i] if not isinstance(TwH[i], dict) else TwH[i]["value"]
+ if isinstance(TwH[i], dict):
+     import pandas as pd
+     _csvfile = TwH[i]["filename"].replace("$cfgdir", basedir)
+     _tw_data = pd.read_csv(_csvfile, sep=",")
+     Tw_inlet = float(_tw_data["Tw"].iloc[0])
+ else:
+     Tw_inlet = TwH[i]
```

---

### 3.3  `feelpp.py` — Bug 3: empty `dTwH` not handled

When no `dTwH` parameters exist (pattern finds nothing), the extracted list is empty. Must default to zeros.

**Location:** `_build_input_from_feelpp`, just before the per-channel `for` loop (H-mode branch).

```diff
  dTwH = [parameters[p] for p in p_params["dTwH"]]
+ if not dTwH:
+     dTwH = [0.0] * len(Dh)
```

---

### 3.4  `feelpp.py` — Bug 4: incomplete axial CSV save in `_extract_parameter_updates`

The `pass` block where axial distribution data should be saved back to CSV must be completed.

**Location:** `_extract_parameter_updates`, H-mode branch.

```diff
- if channel_out.temp_distribution:
-     # This needs the Tw_dict info to save properly
-     # Implementation depends on how you want to handle this
-     pass
+ if channel_out.temp_distribution:
+     TwH_params = p_params.get("TwH", [])
+     if i < len(TwH_params):
+         _twh_val = parameters.get(TwH_params[i])
+         if isinstance(_twh_val, dict):
+             import pandas as pd
+             _csvfile = _twh_val["filename"].replace("$cfgdir", basedir)
+             _tw_data = pd.read_csv(_csvfile, sep=",")
+             _tw_data["Tw"] = channel_out.temp_distribution
+             if args.cooling == "gradHZH" and channel_out.heat_coeff_distribution:
+                 _tw_data["hw"] = channel_out.heat_coeff_distribution
+             elif "hw" in _tw_data.columns:
+                 _tw_data = _tw_data.drop(columns=["hw"])
+             _tw_data.to_csv(_csvfile, index=False)
```

Note: `_extract_parameter_updates` needs `parameters` and `basedir` passed in, or the TwH dict info obtained another way. Consider adding `parameters: dict` and `basedir: str` as additional parameters to this method if they are not already available in scope.

---

### 3.5  `feelpp.py` — Bug 5: `ChannelOutput` has no `geometry` attribute

After fix §3.0, use `channel_out.name` directly.

**Location:** `_update_dict_df`, top of loop body.

```diff
- cname = channel_out.geometry.name if hasattr(channel_out, "geometry") else f"ch_{i}"
+ cname = channel_out.name if channel_out.name else f"ch_{i}"
```

---

### 3.6  `feelpp.py` — Bug 6: wrong key check for `cf` DataFrame

`dict_df[target]` has no key `"H"`. The check for the friction-factor column should test for `"cf"`.

**Location:** `_update_dict_df`, conditional for `cf`.

```diff
- if "H" in dict_df[target] and hasattr(channel_out, "friction_factor"):
+ if "cf" in dict_df[target]:
```

---

## 4. API Mapping: `waterflow` → `WaterFlow`

Both classes read the same JSON parameter file format (`Vp0`, `Vpmax`, `F0`, `Fmax`, `Pmax`, `Pmin`, `BP`, `Imax`).

| Old (`python_magnetworkflows.waterflow`) | New (`python_magnetcooling.WaterFlow`) |
|---|---|
| `waterflow.flow_params(filename)` | `WaterFlow.from_file(filename)` |
| `w.flow(current)` | `w.flow_rate(current)` |
| `w.pressure(current)` | `w.pressure(current)` *(unchanged)* |
| `w.dpressure(current)` | `w.pressure_drop(current)` |
| `w.umean(current, section)` | `w.velocity(current, section)` |
| `w.vpump(current)` | `w.pump_speed(current)` |

The feelpp.py adapter already holds a reference to the waterflow object via `targets[target]["waterflow"]`. After migration, that object will be a `WaterFlow` instance (created in `cli.py`).

---

## 5. Backup Local Modules

Before deleting, create copies (committed to the repo for reference):

```bash
cp python_magnetworkflows/python_magnetworkflows/cooling.py \
   python_magnetworkflows/python_magnetworkflows/cooling.py.bak
cp python_magnetworkflows/python_magnetworkflows/waterflow.py \
   python_magnetworkflows/python_magnetworkflows/waterflow.py.bak
git add python_magnetworkflows/python_magnetworkflows/cooling.py.bak \
        python_magnetworkflows/python_magnetworkflows/waterflow.py.bak
```

---

## 6. Changes to `error.py`

### 6a. Import block (lines 3–5)

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

### 6b. Replace the cooling update block (current lines 434–828)

The block starts with `if args.update_cooling:` (keep this guard) and spans both the per-channel ("H") and global code paths.

Replace everything from `if args.update_cooling:` through the two `del` statements just before `err_max_dT = max(...)` with:

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

### 6c. Replace `getTout` call for site-level mixing (currently near line 830)

```python
# REMOVE:
Tout_site = getTout(List_Tout, List_VolMassout, List_SpecHeatout, List_Qout)

# ADD:
Tout_site = compute_mixed_outlet_temperature(
    List_Tout, List_VolMassout, List_SpecHeatout, List_Qout
)
```

---

## 7. Changes to `cli.py`

### 7a. Import block (lines 18–19)

```python
# REMOVE:
from .waterflow import waterflow
from .cooling import getDT, getHeatCoeff

# ADD:
from python_magnetcooling import WaterFlow
from python_magnetcooling.cooling import getDT, getHeatCoeff
```

`getDT` and `getHeatCoeff` are stored as callable references in heat param config dicts (lines 356, 367, 381, 392). They are never called via that dict key, but the references are kept for metadata purposes.

### 7b. Waterflow instantiation in `configure_magnet_target` (line 588)

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

No other changes needed in `cli.py`. Any remaining direct calls to waterflow methods in `error.py` (inside `if args.update_cooling:`) use the object stored in `targets[target]["waterflow"]` — after cli.py is updated, this will be a `WaterFlow` instance with the new method names. The adapter's `_build_input_from_feelpp` already uses `waterflow.pressure()` and `waterflow.pressure_drop()` (after the Bug 1 patch), so no further changes are needed in error.py for these.

---

## 8. Remove Local Modules

```bash
git rm python_magnetworkflows/python_magnetworkflows/cooling.py
git rm python_magnetworkflows/python_magnetworkflows/waterflow.py
```

---

## 9. Verification Checklist

```bash
# 1. Import check
python -c "from python_magnetworkflows.error import compute_error; print('error: OK')"
python -c "from python_magnetworkflows.cli import main; print('cli: OK')"

# 2. Confirm old modules are gone
python -c "from python_magnetworkflows.cooling import getDT" 2>&1   # expect ImportError
python -c "from python_magnetworkflows.waterflow import waterflow" 2>&1  # expect ImportError

# 3. Run existing tests (if any)
pytest tests/ -v

# 4. Minimal end-to-end smoke test
python_magnetworkflows <cfgfile> \
  --mdata '{"M9":{"type":"helix","value":31000,"flow":"flow.json"}}' \
  --cooling mean --noupdate
```

---

## 10. Relaxation Semantics Note

The current `error.py` applies relaxation **once** at the end of each outer iteration:
```python
dTwi[i] = (1.0 - relax) * tmp_dTwi + relax * dTwH[i]   # new blend with old
```

`ThermalHydraulicCalculator._compute_channel_uniform` in python_magnetcooling applies relaxation **at each inner iteration step** if `relaxation_factor > 0`. To preserve the original outer-iteration relaxation behavior exactly, the adapter is called with `relaxation_factor=0.0` (default in `ThermalHydraulicInput`), and the blending is done in `error.py` after receiving `param_updates` from the adapter (see §6b).

---

## 11. pyproject.toml

Add `python-magnetcooling` to the dependencies list:
```toml
[project]
dependencies = [
    # … existing deps …
    "python-magnetcooling",
]
```
