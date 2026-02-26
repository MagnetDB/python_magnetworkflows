"""
Measure-building and magnet configuration helpers.

Functions to construct regex patterns, measure dictionaries, heat/power
parameters and the target/postvalue configurations consumed by oneconfig.
"""

import os

from python_magnetcooling import WaterFlow
from python_magnetcooling.cooling import getDT, getHeatCoeff

from .magnet_type import (
    MagnetType,
    DEFAULT_FUZZY_FACTOR_BITTER,
    DEFAULT_FUZZY_FACTOR_HELIX,
    DEFAULT_INDUCTANCE,
    DEFAULT_PEXTRA,
    DEFAULT_RELAX,
    validate_magnet_config,
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
    Build power-related measures (PowerM, PowerH, Flux).

    Args:
        magnet_type: Either MagnetType.INSERT or MagnetType.BITTERS
        mfilter: Filter prefix for the magnet
        patterns: Dictionary of regex patterns from build_patterns()

    Returns:
        Dictionary containing PowerM, PowerH, Flux measure definitions
    """
    csv_file = "heat.measures/values.csv"

    return {
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

    return {
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

    return {
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


def configure_magnet_target(
    mfilter: str,
    magnet_type: MagnetType,
    values: dict,
    pwd: str,
    args,
    patterns: dict,
    power_measures: dict,
    heat_params: dict,
    e,
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
            power_measures["PowerH"],
        ],
        "unit": "A",
        "name": f"Intensity_{mfilter}",
        "post": {"type": "Statistics_Intensity", "math": "integrate"},
        "waterflow": WaterFlow.from_file(
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
            "W",
        )
        target_config["computed_params"].append(FluxZ)

    target_config["relax"] = values.get("relax", DEFAULT_RELAX)
    target_config["inductance"] = values.get("inductance", DEFAULT_INDUCTANCE)

    if "heatCorrelationFuzzyFactor" in values:
        target_config["fuzzy"] = values["heatCorrelationFuzzyFactor"]
    elif magnet_type == MagnetType.BITTERS:
        target_config["fuzzy"] = DEFAULT_FUZZY_FACTOR_BITTER
    else:
        target_config["fuzzy"] = DEFAULT_FUZZY_FACTOR_HELIX

    target_config["pextra"] = values.get("pextra", DEFAULT_PEXTRA)

    return target_config


def configure_magnet_postvalues(
    temp_measures: dict,
    mech_measures: dict = None,
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
            temp_measures["MaxT"],
        ],
        "statsTH": [
            temp_measures["MinTH"],
            temp_measures["MeanTH"],
            temp_measures["MaxTH"],
        ],
    }

    if mech_measures:
        postvalue_config["statsDispl"] = [
            mech_measures["MinDispl"],
            mech_measures["MaxDispl"],
        ]
        postvalue_config["statsStress"] = [
            mech_measures["MinStress"],
            mech_measures["MeanStress"],
            mech_measures["MaxStress"],
        ]
        postvalue_config["statsVonMises"] = [
            mech_measures["MinVonMises"],
            mech_measures["MeanVonMises"],
            mech_measures["MaxVonMises"],
        ]
        postvalue_config["statsDisplH"] = [
            mech_measures["MinDisplH"],
            mech_measures["MaxDisplH"],
        ]
        postvalue_config["statsStressH"] = [
            mech_measures["MinStressH"],
            mech_measures["MeanStressH"],
            mech_measures["MaxStressH"],
        ]
        postvalue_config["statsVonMisesH"] = [
            mech_measures["MinVonMisesH"],
            mech_measures["MeanVonMisesH"],
            mech_measures["MaxVonMisesH"],
        ]

    return postvalue_config


def loadMdata(e, pwd: str, args, targets: dict, postvalues: dict):
    """
    Load magnet data configuration.

    Configures targets and postvalues for each magnet defined in args.mdata.

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

        validate_magnet_config(magnet_type, values)

        patterns = build_patterns(magnet_type, mfilter)
        power_measures = build_power_measures(magnet_type, mfilter, patterns)
        heat_params = build_heat_params(magnet_type, mfilter)
        temp_measures = build_temperature_measures(magnet_type, mfilter, patterns)

        mech_measures = None
        if "thmagel" in args.cfgfile:
            mech_measures = build_mechanical_measures(magnet_type, mfilter, patterns)

        targets[f"{mfilter}I"] = configure_magnet_target(
            mfilter, magnet_type, values, pwd, args,
            patterns, power_measures, heat_params, e
        )
        postvalues[f"{mfilter}I"] = configure_magnet_postvalues(
            temp_measures, mech_measures
        )

    return (targets, postvalues)
