import pandas as pd

from .params import getTarget, getparam, resolve_cfgdir_path
from python_magnetcooling.feelpp import FeelppThermalHydraulicAdapter
from python_magnetcooling.thermohydraulics import (
    ThermalHydraulicCalculator,
    compute_mixed_outlet_temperature,
)
from python_magnetcooling.cooling import steam  # used only for site-level mixing

import re
from tabulate import tabulate

import gc

# Convergence tolerance for iterative flow calculation
FLOW_CONVERGENCE_TOL = 1.0e-3


# sort (ref https://stackoverflow.com/questions/29580978/naturally-sorting-pandas-dataframe)
def natsortdataframe(pd):
    """
    perform natsort on pandas dataframe

    returns sorted dataframes
    """
    from natsort import natsorted

    sorted_columns = natsorted(list(pd.columns))
    return pd[sorted_columns]


def natsortlist(list_):
    """
    perform natsort on list

    returns sorted list
    """
    from natsort import natsorted

    return natsorted(list_)


def init_dict_df(targets: dict, args):
    dict_df = {}
    for target, values in targets.items():
        # print(f"{target}: {values['objectif']}", flush=True)
        dict_df[target] = {
            "target": float(values["objectif"]),
            "flow": 0.0,
            "Tout": 0.0,
            "MSite_Tout": 0.0,
            "L": float(values["inductance"]),
            "PowerM": pd.DataFrame(),
            "PowerH": pd.DataFrame(),
            "Flux": pd.DataFrame(),
            "HeatCoeff": pd.DataFrame(),
            "DT": pd.DataFrame(),
            "Uw": pd.DataFrame(),
        }
        if "H" in args.cooling:
            dict_df[target]["cf"] = pd.DataFrame()

        dict_df[target]["statsT"] = {
            "MinT": pd.DataFrame(),
            "MaxT": pd.DataFrame(),
            "MeanT": pd.DataFrame(),
        }
        dict_df[target]["statsTH"] = {
            "MinTH": pd.DataFrame(),
            "MaxTH": pd.DataFrame(),
            "MeanTH": pd.DataFrame(),
        }

        if "thmagel" in args.cfgfile:
            dict_df[target]["statsDispl"] = {
                "MinDispl": pd.DataFrame(),
                "MaxDispl": pd.DataFrame(),
                "MeanDispl": pd.DataFrame(),
            }
            dict_df[target]["statsStress"] = {
                "MinStress": pd.DataFrame(),
                "MaxStress": pd.DataFrame(),
                "MeanStress": pd.DataFrame(),
            }
            dict_df[target]["statsVonMises"] = {
                "MinVonMises": pd.DataFrame(),
                "MaxVonMises": pd.DataFrame(),
                "MeanVonMises": pd.DataFrame(),
            }
            dict_df[target]["statsDisplH"] = {
                "MinDisplH": pd.DataFrame(),
                "MaxDisplH": pd.DataFrame(),
                "MeanDisplH": pd.DataFrame(),
            }
            dict_df[target]["statsStressH"] = {
                "MinStressH": pd.DataFrame(),
                "MaxStressH": pd.DataFrame(),
                "MeanStressH": pd.DataFrame(),
            }
            dict_df[target]["statsVonMisesH"] = {
                "MinVonMisesH": pd.DataFrame(),
                "MaxVonMisesH": pd.DataFrame(),
                "MeanVonMisesH": pd.DataFrame(),
            }

    return dict_df


def read_measures_csv(measures_csv: dict, filename: str, debug: bool) -> dict:
    with open(filename, "r") as file:
        if debug:
            print(f"read csv: {filename}", flush=True)
        measures_csv[filename] = pd.read_csv(file, sep=",")
        if debug:
            print(f"*** measures_csv[{filename}]: {measures_csv[filename].columns.values.tolist()}", flush=True)
    return measures_csv


def compute_error(
    e,
    f,
    basedir: str,
    it: int,
    args,
    targets: dict,
    postvalues: dict,
    params: dict,
    parameters: dict,
):
    """
    it: actual iteration number
    args:
    e: feelpp env
    f: feelpp problem
    targets: dict of target
    params: dict(target, params:list of parameters name)
    parameters: all jsonmodel parameters
    dict_df:
    """
    print(f"*** compute_error: it={it}, targets={targets}, cooling={args.cooling}", flush=True)
    dict_df = init_dict_df(targets, args)

    #y a un pb d'algo dans le cas: gradHZ  
    # avec les noms des sorties du post pour la partie "Flux" 
    # ("FluxZ" uniquement alors qu'on cherche une entree "Flux" -- error.py)

    table_ = [it]
    err_max = 0.0
    err_max_dT = 0.0
    err_max_h = 0.0

    List_Tout = []
    List_VolMassout = []
    List_SpecHeatout = []
    List_Qout = []
    Tw0 = None

    measures_csv = {}  # create dict for export csv to open them only once
    for target, values in targets.items():
        print(
            f'dict_df[target]["target"]={dict_df[target]["target"]} (type={type(dict_df[target]["target"])})',
            flush=True,
        )

        objectif = -float(values["objectif"])
        # multiply by -1 because of orientation of pseudo Axi domain Oy == -U_theta

        filename = targets[target]["csv"]
        measures_csv = read_measures_csv(measures_csv, filename, args.debug)
        print(f"{target}: read measures_csv {filename} with {len(measures_csv[filename].columns)} columns", flush=True)

        filtered_df = getTarget(
            targets, target, measures_csv[filename], args.debug
        ).copy(deep=True)
        print(f"{target}: filtered_df has {len(filtered_df.columns)} columns", flush=True)
        relax = float(values["relax"])
        fuzzy = float(values["fuzzy"])
        pextra = float(values.get("pextra", 1))

        # TODO: add stats for filtered_df to table_: mean, ecart type, min/max??

        error = filtered_df.div(-objectif).add(1)
        err_max_target = max(error.abs().max(axis=1))
        err_max = max(err_max_target, err_max)

        if args.debug:
            print(f"filtered_df: {filtered_df.columns.values.tolist()}", flush=True)
            print(f"{target}: objectif={objectif}", flush=True)
            print(f"{target}: err_max_target={err_max_target:.3e}", flush=True)
            print(f"{target}: err_max={err_max:.3e}", flush=True)
            print(f"{target}: relax={relax}", flush=True)
            print(f"{target}: fuzzy={fuzzy}", flush=True)
            # print(f"{target}: filtered_df={filtered_df}", flush=True)
            # print(f"{target}: error={error}", flush=True)
        print(
            f"{target}: it={it}, err_max={err_max_target:.3e}, eps={args.eps:.3e}, itmax={args.itermax}",
            flush=True,
        )

        for param in params[target]:
            if f.mesh().dimension() == 3:
                marker = "V1"
            else:
                marker = param.replace(
                    "U_", ""
                )  # get name from values['control_params'] / change control_params to a list of dict?
            val = filtered_df[marker].iloc[-1]
            ovalue = parameters[param]
            table_.append(ovalue)
            nvalue = ovalue * objectif / val
            if args.debug:
                print(f"param={param}, marker={marker}", flush=True)
                print(
                    f"{it}: {marker}, goal={objectif:.3f}, val={val:.3f}, err={error[marker].iloc[-1]:.3e}, ovalue={ovalue}, nvalue={nvalue}",
                    flush=True,
                )
            # f.addParameterInModelProperties(param, nvalue)
            parameters[param] = nvalue

        del filtered_df
        del error
        table_.append(err_max_target)

        # update bcs
        p_params = {}
        # TODO upload p_df into a dict like {name: p_df} with name = target (aka key of targets)
        # this way we can get p_df per target as an output for solve
        # NB: pd_df[pname] is a pandas dataframe (pname is parameter name, eg Flux)

        for param in values["computed_params"]:
            name = param["name"]
            print(f"{target}: computed_params {name}", flush=True)

            if "csv" in param:
                filename = param["csv"]
                # measures_csv = read_measures_csv(measures_csv, filename, args.debug)

                dict_df[target][name] = getTarget(
                    {f"{name}": param}, name, measures_csv[filename], args.debug
                ).copy(deep=True)
                if args.debug:
                    print(f"{target}: {name}={dict_df[target][name]}", flush=True)
            else:
                if args.debug:
                    print(f"{target}: {name}", flush=True)
                for p in param["params"]:
                    pname = p[0]
                    if args.debug:
                        print(
                            f"{name}: extract params for {p[0]} (len(p)={len(p)})",
                            flush=True,
                        )
                    tmp = getparam(p[0], parameters, p[1], args.debug)
                    if len(p) == 4:
                        regex_match = re.compile(p[2])
                        if p[3]:
                            tmp = [t for t in tmp if regex_match.fullmatch(t)]
                        else:
                            tmp = [t for t in tmp if not regex_match.fullmatch(t)]
                    tmp.sort()
                    # print(f'{name}: sorted tmp={tmp}', flush=True)
                    if pname in p_params:
                        p_params[pname] += tmp
                    else:
                        p_params[pname] = tmp

                    del tmp

        if args.debug:
            print(f"p_df: {dict_df[target].keys()}", flush=True)
            print(f"p_params: {p_params.keys()}", flush=True)
            print(f'p_params[Tw]={p_params["Tw"]}', flush=True)

        # for key in ["statsT", "statsTH"]:
        print(f"{target}: getTarget {postvalues[target].keys()}", flush=True)
        for key in postvalues[target].keys():
            for param in postvalues[target][key]:
                name = param["name"]
                if args.debug:
                    print(f"{target}: postvalues_params {name}", flush=True)

                if "csv" in param:
                    filename = param["csv"]
                    # measures_csv = read_measures_csv(measures_csv, filename, args.debug)
                    dict_df[target][key][name] = getTarget(
                        {f"{name}": param}, name, measures_csv[filename], args.debug
                    ).copy(deep=True)
                    if args.debug:
                        print(f"{target}: postvalues {key} {name}={dict_df[target][key][name]}", flush=True)

        # perform natsort on dataframe and list
        print("Natsort on dataframe and list", flush=True)
        for key, values_ in dict_df[target].items():
            msg = f"dict_df[target]: key={key}, values={type(values_)}"
            if isinstance(values_, dict):
                msg += " dict"
            if isinstance(values_, list):
                if values_:
                    msg += f", list={type(values_[0])}  sorted"
                    dict_df[target][key] = natsortlist(values_).copy()
                else:
                    msg += f", list=empty"
            if isinstance(values_, pd.core.frame.DataFrame):
                msg += " dataframe sorted"
                dict_df[target][key] = natsortdataframe(values_).copy(deep=True)
                msg += f", columns={dict_df[target][key].columns.values.tolist()}"  
            if args.debug:
                print(msg, flush=True)

        for key, values_ in p_params.items():
            msg = f"p_params: key={key}, values={type(values_)}"
            if isinstance(values_, list):
                if values_:
                    msg += f", list={type(values_[0])} sorted"
                    p_params[key] = natsortlist(values_)
                else:
                    msg += f", list=empty"
            if args.debug:
                print(msg, flush=True)

        # if args.cooling == "gradHZ":
        # flux is empty
        # we shall sum all the fluxZ to get the total flux for each channel and compute the error with PowerM
        # if this OK?
        # what happens when args.cooling in [meanH, gradH] ?
        # what happen when args.cooling in [mean, grad]? 
        if args.debug:
            print(f"PowerM: {dict_df[target]['PowerM']}", flush=True)
            print(f"PowerH: {dict_df[target]['PowerH']}", flush=True)
            # for flux_key in [k for k in dict_df[target].keys() if k.startswith("Flux")]:
            #     print(f"{flux_key}: {dict_df[target][flux_key]}", flush=True)
            print(f"Flux: {dict_df[target]['Flux']}", flush=True)

        PowerM = dict_df[target]["PowerM"].iloc[-1, 0]
        SPower_H = dict_df[target]["PowerH"].iloc[-1].sum()
        if args.cooling in ["gradHZ", "gradHZH"]:
            # Create Flux dataframe by aggregating FluxZ columns per channel/slit
            print(f"FluxZ: {dict_df[target]['FluxZ'].keys()}", flush=True)
            print(f"FluxZ: {dict_df[target]['FluxZ']}", flush=True)
            
            # Check for negative values in FluxZ
            fluxz_data = dict_df[target]['FluxZ'].iloc[-1]
            negative_cols = fluxz_data[fluxz_data < 0]
            if not negative_cols.empty:
                print(f"WARNING {target}: FluxZ contains negative values in columns: {negative_cols.to_dict()}", flush=True)
            
            # Get channel/slit names from Dh parameters
            flux_by_channel = {}
            for dh_param in p_params["Dh"]:
                cname = dh_param.replace("Dh_", "")
                # Create regex pattern to match FluxZ columns for this channel
                # e.g., "M9_Bi_Slit0" -> match "FluxZ0_M9_Bi_Slit0", "FluxZ1_M9_Bi_Slit0", etc.
                pattern = re.compile(rf"FluxZ\d+_{re.escape(cname)}$")
                
                # Find all matching FluxZ columns
                matching_cols = [
                    col for col in dict_df[target]["FluxZ"].columns
                    if pattern.match(col)
                ]
                
                if matching_cols:
                    # Sum all FluxZ columns for this channel
                    flux_by_channel[cname] = dict_df[target]["FluxZ"][matching_cols].iloc[-1].sum()
                    if args.debug:
                        print(f"{target}: {cname} - matched columns: {matching_cols}, total flux: {flux_by_channel[cname]:.3f}", flush=True)
                else:
                    if args.debug:
                        print(f"{target}: WARNING - no FluxZ columns found for {cname}", flush=True)
            
            # Create Flux dataframe from aggregated values
            dict_df[target]["Flux"] = pd.DataFrame([flux_by_channel])
            print(f"{target}: created Flux dataframe from FluxZ with columns: {dict_df[target]['Flux'].columns.values.tolist()}", flush=True)
            
        SFlux_H = dict_df[target]["Flux"].iloc[-1].sum()
        print(f"{target}: SFlux_H={SFlux_H:.3f}", flush=True)

        if args.debug:
            print(f'Flux: {type(dict_df[target]["Flux"])}', flush=True)
        sortedflux = dict_df[target]["Flux"].copy(deep=True)
        t_headers = ["Part", "Flux[MW]"]
        t_parts = sortedflux.columns.values.tolist()
        # t_power = sortedflux.iloc[-1]
        t_power = [f"{s/1.e+6:.3f}" for s in sortedflux.iloc[-1].tolist()]
        # print(type(t_power.tolist()), flush=True)
        print(tabulate(list(zip(t_parts, t_power)), headers=t_headers), flush=True)

        Powers_Diff = abs(PowerM - SPower_H)
        PowerFlux_Diff = abs(PowerM - SFlux_H)

        print(
            f"{target}: it={it} Power={PowerM:.3f} SPower_H={SPower_H:.3f} SFlux_H={SFlux_H:.3f}",
            flush=True,
        )
        # print a table with key, power, ucoil
        t_headers = ["Part", "Power[W]", "U[V]"]
        t_parts = dict_df[target]["PowerH"].columns.values.tolist()
        t_power = dict_df[target]["PowerH"].iloc[-1]
        t_U = dict_df[target]["PowerH"].iloc[-1] / dict_df[target]["target"]
        print(
            tabulate(list(zip(t_parts, t_power, t_U)), headers=t_headers),
            flush=True,
        )

        del t_headers
        del t_parts
        del t_power
        del t_U

        if args.debug:
            for key in p_params:
                print(f"{target}: {key}={p_params[key]}", flush=True)

        Ptol = 1e-2
        print(f"{target}: it={it} Power={PowerM:.3f} SPower_H={SPower_H:.3f} SFlux_H={SFlux_H:.3f}  Powers_Diff={Powers_Diff:.3f} PowerFlux_Diff={PowerFlux_Diff:.3f}",)

        if PowerM == 0:
            raise ValueError(
                f"{target}: PowerM is zero at it={it}; cannot evaluate power balance. "
                "Check solver output and boundary conditions."
            )
        assert Powers_Diff / PowerM <= Ptol, (
            f"Power!=SPower_H:{100*Powers_Diff/PowerM:.3f}%  Power={PowerM:.3f} SPower_H={SPower_H:.3f}"
        )
        assert PowerFlux_Diff / PowerM <= Ptol, (
            f"Power!=SFlux_H:{100*PowerFlux_Diff/PowerM:.3f}%   Power={PowerM:.3f} SFlux_H={SFlux_H:.3f}"
        )

        # get dict_df[target]["Flux"] column names
        for i, cname in enumerate(sortedflux.columns.values.tolist()):
            print(
                f'{target} Channel{i} Flux[cname={cname}]: {dict_df[target]["Flux"][cname].iloc[-1]:.3f}',
                flush=True,
            )

        del sortedflux

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

    if args.update_cooling and len(List_Tout) > 1:
        Tout_site = compute_mixed_outlet_temperature(
            List_Tout, List_VolMassout, List_SpecHeatout, List_Qout
        )
        print(f"MSITE Tout={Tout_site}", flush=True)
        dict_df[target]["MSite_Tout"] = Tout_site

    del List_Tout
    del List_VolMassout
    del List_SpecHeatout
    del List_Qout
    del measures_csv
    del objectif
    gc.collect()
    return (err_max, err_max_dT, err_max_h, table_, p_params, parameters, dict_df)
