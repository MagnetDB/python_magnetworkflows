# Testing python_magnetworkflows

## Overview

The test suite is split into two tiers:

| Tier | Files | When they run | Requirements |
|------|-------|---------------|--------------|
| Pure Python | `test_params.py`, `test_args.py`, `test_real_methods.py` | Always | Standard dev dependencies only |
| feelpp-gated | `test_solver.py`, `test_integration.py` | Only when feelpp is installed | feelpp system package + simulation data |

Tests that require feelpp are skipped entirely at collection time (via
`pytest.importorskip`) when the library is absent — no error, no false
failures.

---

## Quick start (no feelpp required)

```bash
# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the pure-Python tests
pytest -m "not feelpp" -v

# Or just run everything (feelpp tests auto-skip)
pytest -v
```

Expected output when feelpp is not installed:
- `test_params.py`, `test_args.py`, `test_real_methods.py`: all pass
- `test_solver.py`, `test_integration.py`: entire files shown as **skipped**

---

## Setting up feelpp

feelpp is distributed as Debian packages from the LNCMI apt repository. It
cannot be installed via `pip`.

```bash
# Add the feelpp apt repository (Ubuntu Noble / Debian 13)
curl -fsSL http://apt.feelpp.org/ubuntu/noble/feelpp.gpg | sudo tee /etc/apt/trusted.gpg.d/feelpp.gpg
echo "deb http://apt.feelpp.org/ubuntu/noble noble latest" | sudo tee /etc/apt/sources.list.d/feelpp.list
sudo apt-get update

# Install required packages
sudo apt-get install -y \
  python3-feelpp \
  python3-feelpp-toolboxes \
  feelpp-toolboxes-coefficientformpdes \
  feelpp-toolboxes-data \
  feelpp-data
```

See `.devcontainer/Dockerfile` for the complete list of packages used in
the development container, and `singularity.def` for the HPC container setup.

### Virtual environment with system packages

Because feelpp is a system package (not pip-installable), you **must**
create the virtual environment with `--system-site-packages`:

```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -e ".[dev]"
```

Without `--system-site-packages`, `import feelpp` will fail even when the
Debian packages are installed.

---

## Pytest markers

| Marker | Meaning | How to deselect |
|--------|---------|-----------------|
| `feelpp` | Requires the feelpp Debian system package | `-m "not feelpp"` |
| `slow` | Requires real simulation data; may run for minutes to hours | `-m "not slow"` |

### Useful invocations

```bash
# Pure Python only (fastest)
pytest -m "not feelpp" -v

# feelpp import/unit tests only (fast, no simulation data needed)
pytest -m "feelpp and not slow" -v

# All feelpp tests including integration (requires MAGNETWORKFLOWS_TEST_DATA)
pytest -m "feelpp" -v

# Full suite
pytest -v
```

---

## Integration tests (simulation data required)

Integration tests in `test_integration.py` actually launch the Feel++
coupled solver. Each test can take several minutes on a typical workstation.
Full commissioning runs (multiple current steps) may take hours.

### Providing test data

Set the `MAGNETWORKFLOWS_TEST_DATA` environment variable to a directory
containing simulation inputs. The structure should mirror the example shell
scripts in `examples/`:

```
$MAGNETWORKFLOWS_TEST_DATA/
├── HLTEST/
│   ├── HLtest-flow_params.json
│   └── mean/
│       ├── HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
│       └── <mesh + json model files>
└── M9Bitters_18MW/
    ├── M9Bitters_18MW-flow_params.json
    └── gradHZ/
        ├── M9Bitters_18MW-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
        └── <mesh + json model files>
```

If `MAGNETWORKFLOWS_TEST_DATA` is not set (or the path does not exist),
all integration tests are automatically skipped with a descriptive message.

### Running integration tests

```bash
export MAGNETWORKFLOWS_TEST_DATA=~/jeremie-simus
pytest -m "feelpp and slow" -v --timeout=3600
```

### Example shell scripts as manual tests

The scripts in `examples/` are manual smoke tests that serve as the
reference for what a passing integration run looks like:

| Script | Magnet type | Notes |
|--------|-------------|-------|
| `examples/HLTEST.sh` | Helix | Single config, `--no-update-cooling` |
| `examples/M9Bitters.sh` | Bitter | Commissioning ramp (multi-step) |
| `examples/Tore_thmagel.sh` | Bitter (thmagel) | Single config |
| `examples/Tore_thmagel_hcurl.sh` | Bitter (thmagel_hcurl) | Single config |
| `examples/Toretest.sh` | Bitter (thmag_hcurl) | Single config |

These scripts expect their working directories to exist under `~/jeremie-simus/`.

---

## CI recommendations

- Run `pytest -m "not feelpp"` in every CI job (no special environment needed).
- Gate `pytest -m "feelpp and not slow"` on a separate job with feelpp
  installed (e.g., using the devcontainer image).
- Gate `pytest -m "feelpp and slow"` on a dedicated job with access to
  simulation data; this job can have a long timeout and run on schedule
  rather than on every commit.
