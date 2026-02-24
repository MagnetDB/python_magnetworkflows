"""
Run feelpp model
"""

import sys
import os
import argparse
import configparser
import json
import re
from enum import Enum
from warnings import simplefilter

import pandas as pd
from natsort import natsorted
from tabulate import tabulate

from .waterflow import waterflow
from .cooling import getDT, getHeatCoeff
from .oneconfig import oneconfig
from .solver import init

# Supress pandas performance warnings
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)


def options(description: str, epilog: str):
    """
    define options
    """

    # command_line = None
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument("cfgfile", help="input cfg file (ex. HL-31.cfg)")

    # TODO: make a group: oneconfig
    # TODO make current a dict: magnet_name: value, targetkey: value
    parser.add_argument("--mdata", help="specify current data", type=json.loads)

    parser.add_argument(
        "--cooling",
        help="choose cooling type",
        type=str,
        choices=["mean", "grad", "meanH", "gradH", "gradHZ"],
        default="mean",
    )
    parser.add_argument(
        "--heatcorrelation",
        help="choose cooling model",
        type=str,
        choices=["Montgomery", "Dittus", "Colburn", "Silverberg"],
        default="Montgomery",
    )
    parser.add_argument(
        "--friction",
        help="choose friction method",
        type=str,
        choices=["Constant", "Blasius", "Filonenko", "Colebrook", "Swamee"],
        default="Constant",
    )
    parser.add_argument(
        "--eps",
        help="specify requested tolerance (default: 1.e-3)",
        type=float,
        default=1.0e-3,
    )
    parser.add_argument(
        "--heatTol",
        help="specify heat tolerance for convergence (default: 1.e-2)",
        type=float,
        default=1.0e-2,
    )
    parser.add_argument(
        "--itermax",
        help="specify maximum iteration (default: 10)",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--update-cooling",
        help="update heat exchange coefficient and water temperature during iterations (default: True)",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-update-cooling",
        help="do not update heat exchange coefficient and water temperature during iterations",
        action="store_false",
        dest="update_cooling",
    )
    parser.add_argument("--reloadcfg", help="get feelpp config", action="store_true", default=True)
    parser.add_argument("--no-reloadcfg", help="do not get feelpp config", action="store_false", dest="reloadcfg")
    
    parser.add_argument("--debug", help="activate debug", action="store_true")
    parser.add_argument("--verbose", help="activate verbose", action="store_true")
    parser.add_argument(
        "--wd",
        help="specify working directory for relative paths (default: '.')",
        type=str,
        default=".",
    )

    return parser


class MagnetType(Enum):
    """Enum for magnet types."""
    INSERT = "helix"
    BITTERS = "bitter"
    SUPRAS = "supra"  # Placeholder for future implementation

    @classmethod
    def from_string(cls, value: str) -> 'MagnetType':
        """Convert string to MagnetType enum."""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(
            f"Invalid magnet type '{value}'. "
            f"Must be one of: {', '.join([m.value for m in cls])}"
        )


# Configuration constants
DEFAULT_FUZZY_FACTOR_HELIX = 1.0
DEFAULT_FUZZY_FACTOR_BITTER = 1.7
DEFAULT_RELAX = 0
DEFAULT_INDUCTANCE = 0
DEFAULT_PEXTRA = 1


def validate_magnet_config(magnet_type: MagnetType, values: dict) -> None:
    """
    Validate magnet configuration parameters.
    
    Args:
        magnet_type: Type of magnet (MagnetType.INSERT or MagnetType.BITTERS)
        values: Configuration values dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    # magnet_type is already validated by MagnetType.from_string()
    
    required_keys = ["type", "value", "flow"]
    missing_keys = [key for key in required_keys if key not in values]
    if missing_keys:
        raise ValueError(
            f"Missing required configuration keys: {', '.join(missing_keys)}"
        )
    
    # Validate numeric values
    if not isinstance(values["value"], (int, float)) or values["value"] <= 0:
        raise ValueError(
            f"Invalid 'value' parameter: {values['value']}. "
            "Must be a positive number."
        )
    
    # Validate optional numeric parameters
    if "relax" in values:
        if not isinstance(values["relax"], (int, float)) or values["relax"] < 0:
            raise ValueError(
                f"Invalid 'relax' parameter: {values['relax']}. "
                "Must be a non-negative number."
            )
    
    if "inductance" in values:
        if not isinstance(values["inductance"], (int, float)) or values["inductance"] < 0:
            raise ValueError(
                f"Invalid 'inductance' parameter: {values['inductance']}. "
                "Must be a non-negative number."
            )
    
    if "heatCorrelationFuzzyFactor" in values:
        if not isinstance(values["heatCorrelationFuzzyFactor"], (int, float)) or values["heatCorrelationFuzzyFactor"] <= 0:
            raise ValueError(
                f"Invalid 'heatCorrelationFuzzyFactor' parameter: {values['heatCorrelationFuzzyFactor']}. "
                "Must be a positive number."
            )
    
    if "pextra" in values:
        if not isinstance(values["pextra"], (int, float)) or values["pextra"] <= 0:
            raise ValueError(
                f"Invalid 'pextra' parameter: {values['pextra']}. "
                "Must be a positive number."
            )


def build_patterns(magnet_type: MagnetType, mfilter: str) -> dict:
    """
    Build regex patterns for a specific magnet type.

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet

    Returns:
        Dictionary of pattern names to regex strings
    """
    if magnet_type == MagnetType.INSERT:
        return {
            "power_m": rf"Statistics_PowerM_{mfilter}\w*integrate",
            "power_h": rf"Statistics_Power_{mfilter}H\d+_integrate",
            "flux": rf"Statistics_Flux_{mfilter}Channel\d+_integrate",
            "flux_z": rf"Statistics_FluxZ\d+_{mfilter}Channel\d+_integrate",
            "intensity": rf"Statistics_Intensity_{mfilter}H\w+_integrate",
            "stat_t_min": rf"Statistics_Stat_T_{mfilter}\w*min",
            "stat_t_mean": rf"Statistics_Stat_T_{mfilter}\w*mean",
            "stat_t_max": rf"Statistics_Stat_T_{mfilter}\w*max",
            "t_min": rf"Statistics_T_{mfilter}\w+\d+_min",
            "t_mean": rf"Statistics_T_{mfilter}\w+\d+_mean",
            "t_max": rf"Statistics_T_{mfilter}\w+\d+_max",
            "stat_displ_min": rf"Statistics_Stat_Displ_{mfilter}\w*min",
            "stat_displ_max": rf"Statistics_Stat_Displ_{mfilter}\w*max",
            "stat_stress_min": rf"Statistics_Stat_Stress_{mfilter}\w*min",
            "stat_stress_mean": rf"Statistics_Stat_Stress_{mfilter}\w*mean",
            "stat_stress_max": rf"Statistics_Stat_Stress_{mfilter}\w*max",
            "stat_vonmises_min": rf"Statistics_Stat_VonMises_{mfilter}\w*min",
            "stat_vonmises_mean": rf"Statistics_Stat_VonMises_{mfilter}\w*mean",
            "stat_vonmises_max": rf"Statistics_Stat_VonMises_{mfilter}\w*max",
            "displ_min": rf"Statistics_Displ_{mfilter}\w+\d+_min",
            "displ_max": rf"Statistics_Displ_{mfilter}\w+\d+_max",
            "stress_min": rf"Statistics_Stress_{mfilter}\w+\d+_min",
            "stress_mean": rf"Statistics_Stress_{mfilter}\w+\d+_mean",
            "stress_max": rf"Statistics_Stress_{mfilter}\w+\d+_max",
            "vonmises_min": rf"Statistics_VonMises_{mfilter}\w+\d+_min",
            "vonmises_mean": rf"Statistics_VonMises_{mfilter}\w+\d+_mean",
            "vonmises_max": rf"Statistics_VonMises_{mfilter}\w+\d+_max",
        }
    elif magnet_type == MagnetType.BITTERS:
        return {
            "power_m": rf"Statistics_PowerM_{mfilter}\w*integrate",
            "power_h": rf"Statistics_Power_{mfilter}\w+_B\d+_integrate",
            "flux": rf"Statistics_Flux_{mfilter}\w+_Slit\d+_integrate",
            "flux_z": rf"Statistics_FluxZ\d+_{mfilter}\w+_Slit\d+_integrate",
            "intensity": rf"Statistics_Intensity_{mfilter}\w+_integrate",
            "stat_t_min": rf"Statistics_Stat_T_{mfilter}\w*min",
            "stat_t_mean": rf"Statistics_Stat_T_{mfilter}\w*mean",
            "stat_t_max": rf"Statistics_Stat_T_{mfilter}\w*max",
            "t_min": rf"Statistics_T_{mfilter}\w+_B\d+_min",
            "t_mean": rf"Statistics_T_{mfilter}\w+_B\d+_mean",
            "t_max": rf"Statistics_T_{mfilter}\w+_B\d+_max",
            "stat_displ_min": rf"Statistics_Stat_Displ_{mfilter}\w*min",
            "stat_displ_max": rf"Statistics_Stat_Displ_{mfilter}\w*max",
            "stat_stress_min": rf"Statistics_Stat_Stress_{mfilter}\w*min",
            "stat_stress_mean": rf"Statistics_Stat_Stress_{mfilter}\w*mean",
            "stat_stress_max": rf"Statistics_Stat_Stress_{mfilter}\w*max",
            "stat_vonmises_min": rf"Statistics_Stat_VonMises_{mfilter}\w*min",
            "stat_vonmises_mean": rf"Statistics_Stat_VonMises_{mfilter}\w*mean",
            "stat_vonmises_max": rf"Statistics_Stat_VonMises_{mfilter}\w*max",
            "displ_min": rf"Statistics_Displ_{mfilter}\w+_B\d+_min",
            "displ_max": rf"Statistics_Displ_{mfilter}\w+_B\d+_max",
            "stress_min": rf"Statistics_Stress_{mfilter}\w+_B\d+_min",
            "stress_mean": rf"Statistics_Stress_{mfilter}\w+_B\d+_mean",
            "stress_max": rf"Statistics_Stress_{mfilter}\w+_B\d+_max",
            "vonmises_min": rf"Statistics_VonMises_{mfilter}\w+_B\d+_min",
            "vonmises_mean": rf"Statistics_VonMises_{mfilter}\w+_B\d+_mean",
            "vonmises_max": rf"Statistics_VonMises_{mfilter}\w+_B\d+_max",
        }
    else:
        raise ValueError(f"Unknown magnet type: {magnet_type}")


def create_measure_dict(
    name: str,
    csv: str,
    rematch: str,
    post_type: str,
    post_math: str,
    unit: str,
    params: list = None,
    control_params: list = None,
) -> dict:
    """
    Factory function for creating measurement dictionaries.
    
    Args:
        name: Name of the measure
        csv: Path to CSV file
        rematch: Regex pattern for matching
        post_type: Post-processing type
        post_math: Post-processing math operation
        unit: Unit of measurement
        params: Optional list of parameters
        control_params: Optional list of control parameters
        
    Returns:
        Dictionary with measurement configuration
    """
    return {
        "name": name,
        "csv": csv,
        "rematch": rematch,
        "params": params or [],
        "control_params": control_params or [],
        "unit": unit,
        "post": {"type": post_type, "math": post_math},
    }


def build_power_measures(magnet_type: MagnetType, mfilter: str, patterns: dict) -> dict:
    """
    Build power-related measures (PowerM, PowerH, Flux, FluxZ).

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet
        patterns: Dictionary of regex patterns from build_patterns()
        
    Returns:
        Dictionary containing PowerM, PowerH, Flux measure definitions
    """
    csv_file = "heat.measures/values.csv"
    
    measures = {
        "PowerM": create_measure_dict(
            "PowerM", csv_file, patterns["power_m"],
            "Statistics_PowerM", "integrate", "W"
        ),
        "PowerH": create_measure_dict(
            "PowerH", csv_file, patterns["power_h"],
            "Statistics_Power", "integrate", "W"
        ),
        "Flux": create_measure_dict(
            "Flux", csv_file, patterns["flux"],
            "Statistics_Flux", "integrate", "W"
        ),
    }
    
    return measures


def build_heat_params(magnet_type: MagnetType, mfilter: str) -> dict:
    """
    Build heat coefficient and temperature parameters.

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet

    Returns:
        Dictionary containing HeatCoeff and DT parameter definitions
    """
    if magnet_type == MagnetType.INSERT:
        heat_coeff = {
            "name": "HeatCoeff",
            "params": [
                ("Dh", f"Dh_{mfilter}\\w+"),
                ("Sh", f"Sh_{mfilter}\\w+"),
                ("hw", f"hw_{mfilter}Channel"),
                ("hwH", f"hw_{mfilter}Channel\\d+"),
                ("Zmax", f"Zmax_{mfilter}Channel"),
                ("ZmaxH", f"Zmax_{mfilter}Channel\\d+"),
            ],
            "value": (getHeatCoeff),
            "unit": "W/m2/K",
        }
        dt = {
            "name": "DT",
            "params": [
                ("Tw", f"Tw_{mfilter}Channel"),
                ("dTw", f"dTw_{mfilter}Channel"),
                ("TwH", f"Tw_{mfilter}Channel\\d+"),
                ("dTwH", f"dTw_{mfilter}Channel\\d+"),
            ],
            "value": (getDT),
            "unit": "K",
        }
    elif magnet_type == MagnetType.BITTERS:
        heat_coeff = {
            "name": "HeatCoeff",
            "params": [
                ("Dh", f"Dh_{mfilter}\\w+"),
                ("Sh", f"Sh_{mfilter}\\w+"),
                ("hw", f"hw_{mfilter}\\w+", "\\w+_Slit\\w+", False),
                ("hwH", f"hw_{mfilter}\\w+", "\\w+_Slit\\w+", True),
                ("Zmax", f"Zmax_{mfilter}\\w+", "\\w+_Slit\\w+", False),
                ("ZmaxH", f"Zmax_{mfilter}\\w+", "\\w+_Slit\\w+", True),
            ],
            "value": (getHeatCoeff),
            "unit": "W/m2/K",
        }
        dt = {
            "name": "DT",
            "params": [
                ("Tw", f"Tw_{mfilter}\\w+", "\\w+_Slit\\w+", False),
                ("dTw", f"dTw_{mfilter}\\w+", "\\w+_Slit\\w+", False),
                ("TwH", f"Tw_{mfilter}\\w+", "\\w+_Slit\\w+", True),
                ("dTwH", f"dTw_{mfilter}\\w+", "\\w+_Slit\\w+", True),
            ],
            "value": (getDT),
            "unit": "K",
        }
    else:
        raise ValueError(f"Unknown magnet type: {magnet_type}")
    
    return {"HeatCoeff": heat_coeff, "DT": dt}


def build_temperature_measures(magnet_type: MagnetType, mfilter: str, patterns: dict) -> dict:
    """
    Build all temperature-related measures (MinT, MeanT, MaxT, MinTH, MeanTH, MaxTH).

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet
        patterns: Dictionary of regex patterns from build_patterns()
        
    Returns:
        Dictionary containing temperature measure definitions
    """
    csv_file = "heat.measures/values.csv"
    
    measures = {
        "MinT": create_measure_dict(
            "MinT", csv_file, patterns["stat_t_min"],
            "Statistics_Stat_T", "min", "K"
        ),
        "MeanT": create_measure_dict(
            "MeanT", csv_file, patterns["stat_t_mean"],
            "Statistics_Stat_T", "mean", "K"
        ),
        "MaxT": create_measure_dict(
            "MaxT", csv_file, patterns["stat_t_max"],
            "Statistics_Stat_T", "max", "K"
        ),
        "MinTH": create_measure_dict(
            "MinTH", csv_file, patterns["t_min"],
            "Statistics_T", "min", "K"
        ),
        "MeanTH": create_measure_dict(
            "MeanTH", csv_file, patterns["t_mean"],
            "Statistics_T", "mean", "K"
        ),
        "MaxTH": create_measure_dict(
            "MaxTH", csv_file, patterns["t_max"],
            "Statistics_T", "max", "K"
        ),
    }
    
    return measures


def build_mechanical_measures(magnet_type: MagnetType, mfilter: str, patterns: dict) -> dict:
    """
    Build all mechanical-related measures (displacement, stress, von Mises).

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet
        patterns: Dictionary of regex patterns from build_patterns()
        
    Returns:
        Dictionary containing mechanical measure definitions
    """
    csv_file = "elastic.measures/values.csv"
    
    measures = {
        "MinDispl": create_measure_dict(
            "MinDispl", csv_file, patterns["stat_displ_min"],
            "Statistics_Stat_Displ", "min", "m"
        ),
        "MaxDispl": create_measure_dict(
            "MaxDispl", csv_file, patterns["stat_displ_max"],
            "Statistics_Stat_Displ", "max", "m"
        ),
        "MinStress": create_measure_dict(
            "MinStress", csv_file, patterns["stat_stress_min"],
            "Statistics_Stat_Stress", "min", "Pa"
        ),
        "MeanStress": create_measure_dict(
            "MeanStress", csv_file, patterns["stat_stress_mean"],
            "Statistics_Stat_Stress", "mean", "Pa"
        ),
        "MaxStress": create_measure_dict(
            "MaxStress", csv_file, patterns["stat_stress_max"],
            "Statistics_Stat_Stress", "max", "Pa"
        ),
        "MinVonMises": create_measure_dict(
            "MinVonMises", csv_file, patterns["stat_vonmises_min"],
            "Statistics_Stat_VonMises", "min", "Pa"
        ),
        "MeanVonMises": create_measure_dict(
            "MeanVonMises", csv_file, patterns["stat_vonmises_mean"],
            "Statistics_Stat_VonMises", "mean", "Pa"
        ),
        "MaxVonMises": create_measure_dict(
            "MaxVonMises", csv_file, patterns["stat_vonmises_max"],
            "Statistics_Stat_VonMises", "max", "Pa"
        ),
        "MinDisplH": create_measure_dict(
            "MinDisplH", csv_file, patterns["displ_min"],
            "Statistics_Displ", "min", "m"
        ),
        "MaxDisplH": create_measure_dict(
            "MaxDisplH", csv_file, patterns["displ_max"],
            "Statistics_Displ", "max", "m"
        ),
        "MinStressH": create_measure_dict(
            "MinStressH", csv_file, patterns["stress_min"],
            "Statistics_Stress", "min", "Pa"
        ),
        "MeanStressH": create_measure_dict(
            "MeanStressH", csv_file, patterns["stress_mean"],
            "Statistics_Stress", "mean", "Pa"
        ),
        "MaxStressH": create_measure_dict(
            "MaxStressH", csv_file, patterns["stress_max"],
            "Statistics_Stress", "max", "Pa"
        ),
        "MinVonMisesH": create_measure_dict(
            "MinVonMisesH", csv_file, patterns["vonmises_min"],
            "Statistics_VonMises", "min", "Pa"
        ),
        "MeanVonMisesH": create_measure_dict(
            "MeanVonMisesH", csv_file, patterns["vonmises_mean"],
            "Statistics_VonMises", "mean", "Pa"
        ),
        "MaxVonMisesH": create_measure_dict(
            "MaxVonMisesH", csv_file, patterns["vonmises_max"],
            "Statistics_VonMises", "max", "Pa"
        ),
    }
    
    return measures


def configure_magnet_target(
    mfilter: str,
    magnet_type: MagnetType,
    values: dict,
    pwd: str,
    args,
    patterns: dict,
    power_measures: dict,
    heat_params: dict,
    e
) -> dict:
    """
    Configure a single magnet target entry.

    Args:
        mfilter: Filter prefix for the magnet
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        values: Magnet configuration values from args.mdata
        pwd: Working directory path
        args: Command-line arguments
        patterns: Regex patterns for this magnet type
        power_measures: Dictionary containing PowerM, PowerH, Flux
        heat_params: Dictionary containing HeatCoeff, DT
        e: Feel++ environment

    Returns:
        Target configuration dictionary
    """
    # Determine target parameters based on magnet type
    if magnet_type == MagnetType.INSERT:
        target_rematch = f"Statistics_Intensity_{mfilter}H\\w+_integrate"
    elif magnet_type == MagnetType.BITTERS:
        target_rematch = f"Statistics_Intensity_{mfilter}\\w+_integrate"
    elif magnet_type == MagnetType.SUPRAS:
        raise NotImplementedError("SUPRAS magnet type is not yet implemented")
    else:
        raise ValueError(f"Unknown magnet type: {magnet_type}")

    target_params = [("N", f"N_{mfilter}\\w+")]
    target_control_params = [(f"{mfilter}U", f"U_{mfilter}\\w+")]

    # Build base target configuration
    target_config = {
        "objectif": values["value"],
        "type": magnet_type.value,
        "csv": "heat.measures/values.csv",
        "rematch": target_rematch,
        "params": target_params,
        "control_params": target_control_params,
        "computed_params": [
            heat_params["HeatCoeff"],
            heat_params["DT"],
            power_measures["Flux"],
            power_measures["PowerM"],
            power_measures["PowerH"]
        ],
        "unit": "A",
        "name": f"Intensity_{mfilter}",
        "post": {"type": "Statistics_Intensity", "math": "integrate"},
        "waterflow": waterflow.flow_params(
            values["flow"]
            if os.path.isabs(values["flow"])
            else os.path.join(pwd, values["flow"])
        ),
    }
    
    # Add FluxZ if using Z-gradient cooling
    if "Z" in args.cooling:
        if e.isMasterRank():
            print(f"add FluxZ for {magnet_type.value}")
        FluxZ = create_measure_dict(
            "FluxZ",
            "heat.measures/values.csv",
            patterns["flux_z"],
            "Statistics",
            "integrate",
            "W"
        )
        target_config["computed_params"].append(FluxZ)
    
    # Set optional parameters
    target_config["relax"] = values.get("relax", DEFAULT_RELAX)
    target_config["inductance"] = values.get("inductance", DEFAULT_INDUCTANCE)
    
    # Set fuzzy factor (default depends on magnet type)
    if "heatCorrelationFuzzyFactor" in values:
        target_config["fuzzy"] = values["heatCorrelationFuzzyFactor"]
    elif magnet_type == MagnetType.BITTERS:
        target_config["fuzzy"] = DEFAULT_FUZZY_FACTOR_BITTER
    else:
        target_config["fuzzy"] = DEFAULT_FUZZY_FACTOR_HELIX
    
    # Set pextra (extra pressure loss parameter)
    target_config["pextra"] = values.get("pextra", DEFAULT_PEXTRA)
    
    return target_config


def configure_magnet_postvalues(
    temp_measures: dict,
    mech_measures: dict = None
) -> dict:
    """
    Configure post-processing values for a magnet.
    
    Args:
        temp_measures: Dictionary containing temperature measures
        mech_measures: Optional dictionary containing mechanical measures
        
    Returns:
        Post-processing configuration dictionary
    """
    postvalue_config = {
        "statsT": [
            temp_measures["MinT"],
            temp_measures["MeanT"],
            temp_measures["MaxT"]
        ],
        "statsTH": [
            temp_measures["MinTH"],
            temp_measures["MeanTH"],
            temp_measures["MaxTH"]
        ],
    }
    
    # Add mechanical post-processing if available
    if mech_measures:
        postvalue_config["statsDispl"] = [
            mech_measures["MinDispl"],
            mech_measures["MaxDispl"]
        ]
        postvalue_config["statsStress"] = [
            mech_measures["MinStress"],
            mech_measures["MeanStress"],
            mech_measures["MaxStress"]
        ]
        postvalue_config["statsVonMises"] = [
            mech_measures["MinVonMises"],
            mech_measures["MeanVonMises"],
            mech_measures["MaxVonMises"]
        ]
        postvalue_config["statsDisplH"] = [
            mech_measures["MinDisplH"],
            mech_measures["MaxDisplH"]
        ]
        postvalue_config["statsStressH"] = [
            mech_measures["MinStressH"],
            mech_measures["MeanStressH"],
            mech_measures["MaxStressH"]
        ]
        postvalue_config["statsVonMisesH"] = [
            mech_measures["MinVonMisesH"],
            mech_measures["MeanVonMisesH"],
            mech_measures["MaxVonMisesH"]
        ]
    
    return postvalue_config


def loadMdata(e, pwd: str, args, targets: dict, postvalues: dict):
    """
    Load magnet data configuration.
    
    Configures targets and postvalues for each magnet defined in args.mdata.
    Uses helper functions to build patterns, measures, and parameters.
    
    Args:
        e: Feel++ environment
        pwd: Working directory path
        args: Arguments containing magnet data and cooling configuration
        targets: Dictionary to populate with target configurations
        postvalues: Dictionary to populate with post-processing values
        
    Returns:
        Tuple of (targets, postvalues)
    """
    for mname, values in args.mdata.items():
        if e.isMasterRank():
            print(f"mname={mname}, values={values}")
        
        mfilter = values.get("filter", "")
        magnet_type = MagnetType.from_string(values["type"])

        # Validate configuration
        validate_magnet_config(magnet_type, values)

        # Build regex patterns for this magnet type
        patterns = build_patterns(magnet_type, mfilter)

        # Build power measures (PowerM, PowerH, Flux)
        power_measures = build_power_measures(magnet_type, mfilter, patterns)

        # Build heat parameters (HeatCoeff, DT)
        heat_params = build_heat_params(magnet_type, mfilter)

        # Build temperature measures
        temp_measures = build_temperature_measures(magnet_type, mfilter, patterns)

        # Build mechanical measures if using thermo-mechanical coupling
        mech_measures = None
        if "thmagel" in args.cfgfile:
            mech_measures = build_mechanical_measures(magnet_type, mfilter, patterns)

        # Configure target for this magnet
        targets[f"{mfilter}I"] = configure_magnet_target(
            mfilter, magnet_type, values, pwd, args,
            patterns, power_measures, heat_params, e
        )

        # Configure post-processing values for this magnet
        postvalues[f"{mfilter}I"] = configure_magnet_postvalues(
            temp_measures, mech_measures
        )

    return (targets, postvalues)


def exportResults(
    args,
    parameters: dict,
    table,
    table_final,
    dict_df: dict,
    global_df=None,
    suffix: str = None,
):
    # Sum L*I², product I for Mutual
    sumLI2 = 0
    productI = 1
    for target, values in dict_df.items():
        mname = target[:-2]
        prefix = ""
        if mname:
            prefix = f"{mname}_"
        table_final[f"{prefix}I[A]"] = dict_df[target]["target"]
        table_final[f"{prefix}flow[l/s]"] = dict_df[target]["flow"] * 1e3
        table_final[f"{prefix}Tout[K]"] = dict_df[target]["Tout"]
        Tout_site = dict_df[target].get("MSite_Tout")

        sumLI2 += dict_df[target]["L"] * dict_df[target]["target"] ** 2
        productI *= dict_df[target]["target"]

        for key, df in values.items():
            if args.debug:
                print(f"dict key={key}", flush=True)
            if isinstance(df, pd.DataFrame):
                # df is dataframe -> set new index
                df["I"] = f'I={dict_df[target]["target"]}A'
                df.set_index("I", inplace=True)
                df_T = df.T
                if args.debug:
                    print(tabulate(df_T, headers="keys"), flush=True)
                df_T = df_T.reindex(index=natsorted(df_T.index))
                if global_df:  # if commissioning, store in global_df
                    global_df[mname][key] = pd.concat([global_df[mname][key], df])
                else:  # if cli, df to csv
                    outdir = f"{prefix}{key}.measures"
                    os.makedirs(outdir, exist_ok=True)
                    df_T.to_csv(f"{outdir}/values.csv", index=True)

                if key == "PowerM":
                    table_final[f"{prefix}PowerM[MW]"] = df_T.iloc[0, 0] * 1e-6
                elif key == "PowerH":
                    dfUcoil = df / dict_df[target]["target"]
                    for columnName, columnData in dfUcoil.items():
                        if "H" in columnName:
                            # if helix, calculate Ucoil 2 helices by 2
                            nH = int(columnName.split("H", 1)[1])

                            Uname = f"{prefix}Ucoil_H{nH-1}H{nH}[V]"
                            if nH % 2:
                                Uname = f"{prefix}Ucoil_H{nH}H{nH+1}[V]"

                            if Uname in table_final.columns:
                                table_final[Uname] += columnData.iloc[-1]
                            else:
                                table_final[Uname] = columnData.iloc[-1]

                        else:
                            table_final[f"{prefix}Ucoil_{columnName}[V]"] = (
                                columnData.iloc[-1]
                            )

            elif isinstance(df, dict):
                # df is a dict of df, change index and concat them in a single dataframe
                list_dfT = []
                for _key, _df in df.items():
                    if isinstance(_df, pd.DataFrame):
                        _df["I"] = f'{_key}_I={dict_df[target]["target"]}A'
                        _df.set_index("I", inplace=True)
                        print(f"append to list_dfT (key={_key}, col={len(_df.columns.tolist())}):\n{_df}", flush=True)
                        list_dfT.append(_df)
                # list_dfT = [_df for keyT, _df in df.items() if isinstance(dfT, pd.DataFrame)]
                if args.debug:
                    print(f"keys={[keyT for keyT, dfT in df.items()]}", flush=True)
                    for _dft in list_dfT:
                        print(tabulate(_dft, headers="keys"), flush=True)
                        print("\n", flush=True)
                dfT = pd.concat(list_dfT, sort=True)
                if args.debug:
                    print(f"dfT.keys={dfT.keys()}", flush=True)
                    print(f"dfT:\n{dfT}", flush=True)
                dfT_T = dfT.T
                dfT_T = dfT_T.reindex(index=natsorted(dfT_T.index))
                if args.debug:
                    print(f"dfT_T.keys={dfT.keys()}", flush=True)
                    print(f"dfT_T:\n{dfT_T}", flush=True)
                if global_df:  # if commissioning, store in global_df
                    global_df[mname][key] = pd.concat([global_df[mname][key], dfT])
                else:  # if cli, df to csv
                    outdir = f"{prefix}{key}.measures"
                    os.makedirs(outdir, exist_ok=True)
                    dfT_T.to_csv(f"{outdir}/values.csv", index=True)

                if key.endswith("H"):
                    # if TH, DisplH, StressH, VonMisesH: go also in table_final
                    symbol = key.replace("stats", "")
                    T_method = {
                        "Min": min,
                        "Max": max,
                    }
                    T_unit = {
                        "statsTH": "K",
                        "statsDisplH": "m",
                        "statsStressH": "Pa",
                        "statsVonMisesH": "Pa",
                    }
                    for columnName, columnData in dfT.items():
                        if args.debug:
                            print(f"columnName={columnName}", flush=True)
                            print(f"columnData={columnData.keys()}", flush=True)
                        for T in ["Min", "Max"]:
                            if "H" in columnName:
                                # if helices, calculate measures 2 helices by 2
                                nH = int(columnName.split("H", 1)[1])

                                Tname = (
                                    f"{prefix}{T}{symbol}_H{nH-1}H{nH}[{T_unit[key]}]"
                                )
                                if nH % 2:
                                    Tname = f"{prefix}{T}{symbol}_H{nH}H{nH+1}[{T_unit[key]}]"

                                if Tname in table_final.columns:
                                    table_final[Tname] = T_method[T](
                                        table_final[Tname].iloc[-1],
                                        dfT.loc[
                                            f'{T}{symbol}_I={dict_df[target]["target"]}A'
                                        ][columnName],
                                    )
                                else:
                                    table_final[Tname] = dfT.loc[
                                        f'{T}{symbol}_I={dict_df[target]["target"]}A'
                                    ][columnName]

                            elif not re.search(r"_?R\d+", columnName):
                                table_final[
                                    f"{prefix}{T}{symbol}_{columnName}[{T_unit[key]}]"
                                ] = dfT.loc[
                                    f'{T}{symbol}_I={dict_df[target]["target"]}A'
                                ][
                                    columnName
                                ]
                        if symbol != "DisplH":  # DisplH doesn't have mean <- fix !
                            if "H" in columnName:
                                # if helices, calculate mean 2 helices by 2 with area values
                                nH = int(columnName.split("H", 1)[1])

                                Tname = (
                                    f"{prefix}Mean{symbol}_H{nH-1}H{nH}[{T_unit[key]}]"
                                )
                                if nH % 2:
                                    Tname = f"{prefix}Mean{symbol}_H{nH}H{nH+1}[{T_unit[key]}]"
                                    Area = (
                                        parameters[f"Area_{prefix}H{nH}"]
                                        + parameters[f"Area_{prefix}H{nH+1}"]
                                    )
                                else:
                                    Area = (
                                        parameters[f"Area_{prefix}H{nH-1}"]
                                        + parameters[f"Area_{prefix}H{nH}"]
                                    )

                                if Tname in table_final.columns:
                                    table_final[Tname] = (
                                        table_final[Tname].iloc[-1]
                                        + dfT.loc[
                                            f'Mean{symbol}_I={dict_df[target]["target"]}A'
                                        ][columnName]
                                        * parameters[f"Area_{prefix}H{nH}"]
                                    ) / Area
                                else:
                                    table_final[Tname] = (
                                        dfT.loc[
                                            f'Mean{symbol}_I={dict_df[target]["target"]}A'
                                        ][columnName]
                                        * parameters[f"Area_{prefix}H{nH}"]
                                    )

                            elif not re.search(r"_?R\d+", columnName):
                                table_final[
                                    f"{prefix}Mean{symbol}_{columnName}[{T_unit[key]}]"
                                ] = dfT.loc[
                                    f'Mean{symbol}_I={dict_df[target]["target"]}A'
                                ][
                                    columnName
                                ]

        for columnName, columnData in table_final.items():
            # Add R=Ucoil/I to table_final
            if columnName.startswith(f"{prefix}Ucoil"):
                table_final[
                    columnName.replace("Ucoil", "R").replace("[V]", "[ohm]")
                ] = (columnData / dict_df[target]["target"])

        if dict_df[target]["L"] != 0:
            table_final[f"{prefix}L[H]"] = dict_df[target]["L"]

    if not global_df:
        outdir = "U.measures"
        os.makedirs(outdir, exist_ok=True)
        table.to_csv(f"{outdir}/values.csv", index=False)

    if Tout_site:
        table_final["MSite_Tout[K]"] = Tout_site
    if "mag" in args.cfgfile:
        df = pd.read_csv("magnetic.measures/values.csv")
        table_final["B0[T]"] = df["Points_B0_expr_Bz"].iloc[-1]
        if len(dict_df) == 1:
            # if only one magnet calculate inductance
            table_final["L[H]"] = (
                2
                * df["Statistics_MagneticEnergy_integrate"].iloc[-1]
                / (dict_df[target]["target"] ** 2)
            )
        elif sumLI2 != 0:
            # if several magnets, calculate mutual
            table_final["M[H]"] = (
                df["Statistics_MagneticEnergy_integrate"].iloc[-1] - sumLI2 / 2
            ) / productI

    table_final.set_index("measures", inplace=True)
    if suffix is None:
        table_final.T.to_csv("measures.csv", index=True)
    else:
        table_final.T.to_csv(f"measures{suffix}.csv", index=True)

    print(table_final.T)
    return table_final, global_df


def main():
    fname = "cli"
    description = "Cfpdes model"
    epilog = (
        "Setup for Magnet or Site simulation\n"
        "Workflow: actually fix current and compute cooling BCs using selected heatcorrelation\n"
        "\n"
        "Before running you need a flow_params for each magnet\n"
    )
    # print(f"epilog: {epilog} (type={type(epilog)})", flush=True)

    parser = options(description, epilog)
    args = parser.parse_args()
    args.cfgfile = os.path.abspath(args.cfgfile)
    args.wd = os.path.abspath(args.wd)

    pwd = os.getcwd()
    if args.wd != pwd:
        print(f"change working directory to {args.wd}", flush=True)
        os.chdir(args.wd)

    # Load units:
    # TODO force millimeter when args.method == "HDG"
    # units = load_units('meter')

    # Load cfg as config
    dim = 0
    jsonmodel = ""
    meshmodel = ""
    feelpp_config = configparser.ConfigParser()
    basedir = None
    with open(args.cfgfile, "r") as inputcfg:
        feelpp_config.read_string("[DEFAULT]\n[main]\n" + inputcfg.read())
        if "case" in feelpp_config:
            dim = int(feelpp_config["case"]["dimension"])
        else:
            dim = int(feelpp_config["main"]["case.dimension"])
        feelpp_directory = feelpp_config["main"]["directory"]

        basedir = os.path.dirname(args.cfgfile)
        if not basedir:
            basedir = args.wd

        jsonmodel = feelpp_config["cfpdes"]["filename"]
        if jsonmodel.startswith("$cfgdir/"):
            jsonmodel = jsonmodel.replace(r"$cfgdir/", f"{basedir}/")
        # Ensure jsonmodel is always absolute
        if not os.path.isabs(jsonmodel):
            jsonmodel = os.path.abspath(os.path.join(args.wd, jsonmodel))

        meshmodel = feelpp_config["cfpdes"]["mesh.filename"]
        if meshmodel.startswith("$cfgdir/"):
            meshmodel = meshmodel.replace(r"$cfgdir/", f"{basedir}/")
        # Ensure meshmodel is always absolute
        if not os.path.isabs(meshmodel):
            meshmodel = os.path.abspath(os.path.join(args.wd, meshmodel))

    print(f"jsonmodel={jsonmodel}", flush=True)
    print(f"meshmodel={meshmodel}", flush=True)

    # Get Parameters from JSON model file
    parameters = {}
    with open(jsonmodel, "r") as jsonfile:
        dict_json = json.loads(jsonfile.read())
        parameters = dict_json["Parameters"]

    e = None
    (e, f, fields) = init(
        fname,
        e,
        args,
        args.wd,
        jsonmodel,
        meshmodel,
        directory=feelpp_directory,
        dimension=dim,
    )

    if e.isMasterRank():
        print(args)
        print(f"pwd: {args.wd}")
        print(f"feelpp_directory={feelpp_directory}")
        print(f"dim={dim}")
        print(f"basedir={basedir}")
        print(f"jsonmodel={jsonmodel}")
        print(f"meshmodel={meshmodel}")

    targets = {}
    postvalues = {}

    # args.mdata =
    #  currents:  {magnet.name: {'value': current.value, 'type': magnet.type, 'filter': '', 'flow_params': args.flow_params}}
    if args.mdata:
        targets, postvalues = loadMdata(e, args.wd, args, targets, postvalues)

    """
    postvalues = {
        "T": ['MinTH', 'MeanTH', 'MaxTH', 'PowerH'],
        "Stress": ['MinVonMises', 'MinHoop', 'MeanVonMises', 'MeanHoop', 'MaxVonMises', 'MaxHoop']
    }
    # pfields depends from method
    pfields = ['I', 'PowerH', 'MinTH', 'MeanTH', 'MaxTH', 'Flux',
                'MinVonMises', 'MeanVonMises', 'MaxVonMises',
                'MinHoop', 'MeanHoop', 'MaxHoop']
    
    """

    (table, dict_df, e) = oneconfig(
        fname,
        e,
        f,
        fields,
        feelpp_directory,
        jsonmodel,
        meshmodel,
        args,
        targets,
        postvalues,
        parameters,
    )
    if args.debug:
        print(f"oneconfig done, rank={e.worldCommPtr().localRank()}", flush=True)

    if e.isMasterRank():
        print("Export result", flush=True)
        table_final = pd.DataFrame(["values"], columns=["measures"])
        table_final, global_df = exportResults(
            args, parameters, table, table_final, dict_df
        )

    if args.debug:
        print(f"end of cli, rank={e.worldCommPtr().localRank()}", flush=True)

    if args.wd != pwd:  # change back to original working directory
        print(f"change back working directory to {pwd}", flush=True)
        os.chdir(pwd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
