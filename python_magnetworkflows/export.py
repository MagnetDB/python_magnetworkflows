"""
Result export utilities.

Contains exportResults, which aggregates simulation outputs into summary
CSV files and a final measures table.
"""

import os
import re

import pandas as pd
from natsort import natsorted
from tabulate import tabulate


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
