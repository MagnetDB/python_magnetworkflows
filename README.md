# Python Magnet Workflows

Python workflows for coupled electromagnetic-thermal simulations of high-field magnets using Feel++.

## Features

- Iterative solver for coupled physics (electromagnetic + thermal + hydraulic)
- Multiple heat transfer correlations (Montgomery, Dittus-Boelter, Colburn, Silverberg)
- Water cooling system simulation with pressure drop calculations
- Support for helical and bitter magnets
- MPI parallel execution via Feel++

## Requirements

### System Requirements
- Feel++ >= 0.102.1 (must be installed separately)
- Python >= 3.11
- MPI implementation (OpenMPI or MPICH)

### Python Dependencies
See `pyproject.toml` for complete list. Major dependencies:
- numpy, scipy, pandas
- iapws (water properties)
- pint (unit management)
- feelpp and feelpp-toolboxes

## Installation
### Prerequisites

This package requires Feel++ to be installed separately.
For Debian/Ubuntu:

```bash
# Add Feel++ repository
wget -q http://apt.feelpp.org/apt.gpg -O apt.gpg
sudo install -D -o root -g root -m 644 apt.gpg /etc/apt/keyrings/packages.feelpp.gpg
echo "deb http://apt.feelpp.org/ubuntu/noble noble latest" | sudo tee /etc/apt/sources.list.d/feelpp.list

# Install Feel++ Python packages
sudo apt-get update
sudo apt-get install python3-feelpp python3-feelpp-toolboxes python3-feelpp-toolboxes-coefficientformpdes
```

### Python virtual env

For Linux/Mac Os X:

```bash
$ python3 -m venv --system-site-packages magnetworkflows-env
$ source ./magnetworkflows-env/bin/activate
$ python3 -m pip install -e ".[dev]"
```

Use `deactivate` to qui the virtual environment

> [!NOTE]
> * feelpp python packages must be installed before creating the virtual python env. see bellow for details
> * `--system-site-packages` is mandatory since we cannot install feelpp python packages with pip

### Debian/Ubuntu packages

* add lncmi debian repository
* apt update
* apt install ...

## Quick Start
```bash
# Single configuration run
python -m python_magnetworkflows.cli \
  --mdata '{"M9Bitters":{"value":31000,"type":"bitter","filter":"M9Bitters_","flow":"M9Bitters-flow_params.json"}}' \
  M9Bitters-cfpdes-thelec-Axi-sim.cfg \
  --cooling mean \
  --eps 1.e-5

# Commissioning workflow (multiple current steps)
python -m python_magnetworkflows.commissioning \
  --mdata '{"HLtest":{"value":12000,"steplist":[10000,11000,12000],"type":"helix",...}}' \
  config.cfg \
  --cooling gradH
```

## Architecture
```
python_magnetworkflows/
├── cli.py              # Main CLI entry point
├── commissioning.py    # Multi-step commissioning workflows
├── solver.py           # Feel++ solver interface
├── oneconfig.py        # Single configuration solver
├── cooling.py          # Heat transfer correlations
├── waterflow.py        # Hydraulic calculations
├── error.py            # Convergence error calculations
└── params.py           # Parameter extraction utilities
```

## Configuration

Simulations require:
1. Feel++ CFG file (`.cfg`) - solver configuration
2. JSON model file - geometry and material parameters
3. Flow parameters JSON - pump curves and hydraulic data
4. Mesh file (`.msh` or `.json`)

See `README.md` examples section for details.

## Examples

### Running in container

> [!NOTE]
> To check whether or not python_magnetworkflows is installed in the container
>
> ```bash
> singularity exec /home/singularity/feelpp-v0.110.2.sif \
>     dpkg -L python3-magnetworkflows
> ```

In devcontainer, you shall mount your data directory to /home/vscode to run singularity container,eg:

```bash
singularity exec -B /data/M9_M19020601-cfpdes-thmagel_hcurl-nonlinear-Axi-sim/data/geometries:/home/vscode \
    /home/singularity/hifimagnet-salome-9.8.4.sif \
    salome -w1 -t /opt/SALOME-9.8.0-UB20.04/INSTALL/HIFIMAGNET/bin/salome/HIFIMAGNET_Cmd.py args:M9_M19020601.yaml,--axi,--air,4,6
```

```bash
singularity exec -B /data/M9_M19020601-cfpdes-thmagel_hcurl-nonlinear-Axi-sim/data/geometries:/home/vscode \
    /home/singularity/hifimagnet-salome-9.8.4.sif \
    python3 -m python_magnetgeo.xao M9_M19020601-Axi_withAir.xao mesh  --group CoolingChannels --geo M9_M19020601.yaml []
```

```bash
mpirun -np 2 python -m python_magnetworkflows.workflows.cli HL-test-cfpdes-thelec-Axi-sim.cfg --eps 1.e-5
```

### Running multiple configs at once

```bash
python -m python_magnetworkflows.run cli \
   --cfgfile M9Bitters/mean/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
   --mdata '{"M9Bitters":{"value":31000,"type":"bitter","filter":"","relax":0,"flow":"M9Bitters/M9Bitters-flow_params.json"}}'
   --coolings "mean" "meanH" "grad" "gradH" "gradHZ" --hcorrelations "Montgomery" --frictions "Constant"
```


```bash
python -m python_magnetworkflows.run commissioning \
   --cfgfile M9Bitters/mean/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg \
   --mdata '{"M9Bitters":{"value":31000,"step":31000,"stepmax":1,"type":"bitter","filter":"","relax":0,"flow":"M9Bitters/M9Bitters-flow_params.json"}}' \
   --coolings "mean" "meanH" "grad" "gradH" "gradHZ" --hcorrelations "Montgomery" --frictions "Constant"
```

You need a tree structure like :

```
M9Bitters
|_ mean/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
|_ meanH/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
|_ grad/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
|_ gradH/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
|_ gradHZ/M9Bitters-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
```


### testsuite

Create a setup for thelec axi sim for 'M9Bitters_HLtest' site

```bash
export MAGNETDB_API_KEY=
python -m python_magnetapi ...
```

Edit 'tmp/M9Bitters_HLtest/M9Bitters_HLtest-cfpdes-thelec-Axi-sim.json' and modify a U_ parameter

<!-- 
Then create a initial U.h5 file:

```
python -m python_magnetworkflows.create_U tmp/M9Bitters_HLtest/M9Bitters_HLtest-cfpdes-thelec-Axi-sim.cfg
```
 -->

Run the workflow:

```bash
python -m python_magnetworkflows.cli run \
  '{HLtest":{"value":12000,"type":"helix","filter":"HLtest_","flow":"tmp/M9Bitters_HLtest/HLtest-flow_params.json"}, \
            "M9Bitters":{"value":31000,"type":"bitter","filter":"M9Bitters_","flow":"tmp/M9Bitters_HLtest/M9Bitters-flow_params.json"}}' \
  tmp/M9Bitters_HLtest/M9Bitters_HLtest-cfpdes-thelec-Axi-sim.cfg --cooling mean 
```

It must converge in 2 iterations

