"""
Define targets for Axi simulation

structure of a target:
name: 'I'
csv: name of the csv file where name data are recorded
rematch: regexp to recover name data from csv
params from parameters section,
control_params from parameters section,
value: name of the method to compute name
"""

import os
import pandas as pd


def getTarget(
    targetdefs: dict, name: str, csv: pd.DataFrame, debug: bool = False
) -> pd.DataFrame:
    print(f"*** getTarget: cwd={ os.getcwd() } name={name}", flush=True)

    defs = targetdefs[name]

    if debug:
        print(f"getTarget: name={name}, csv_path={defs['csv']}, rematch={defs['rematch']}", flush=True)

        print("csv:")
        for key in csv.columns:
            print(key, csv[key].tolist(), flush=True)

    _filtered_df = csv.filter(regex=(defs["rematch"]))
    if debug:
        print("filtered_csv:")
        for key in _filtered_df.columns:
            print(key, _filtered_df[key].tolist(), flush=True)

    # rename columns
    dict_columns = {}
    for col in _filtered_df.columns:
        cname = col.replace(f'{defs["post"]["type"]}_', "")
        cname = cname.replace(f'_{defs["post"]["math"]}', "")
        dict_columns[col] = cname
    df = _filtered_df.copy(deep=True).rename(columns=dict_columns)

    if debug:
        print(f"getTarget: df for {name}", flush=True)
        for key in df.columns:
            print(key, df[key].tolist(), flush=True)

    del dict_columns
    del defs
    del _filtered_df
    print(f"*** getTarget: done for {name}\n", flush=True)
    return df


def getparam(param: str, parameters: dict, rmatch: str, debug: bool = False) -> list:
    """ """
    # if debug:
    #     print(f"getparam: {param} ====== Start", flush=True)
    # print(f'getparams: param={param}, rmatch={rmatch}, parameters={parameters}')
    val = []

    import re

    regex_match = re.compile(rmatch)
    for p in parameters.keys():
        if regex_match.fullmatch(p):
            # marker = p.split(param + "_")[-1]
            if debug:
                # print(f"match {p}: {marker}")
                print(f"getparam {p}: {parameters[p]}", flush=True)
            val.append(p)

    if debug:
        print(f"getparam val: {val}", flush=True)
        # print(f"getparam: {param} ====== Done", flush=True)
    return val
