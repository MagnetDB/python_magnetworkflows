"""
Run feelpp model
"""

import sys
import os
import configparser
import json
from warnings import simplefilter

import pandas as pd

from .oneconfig import oneconfig
from .solver import init
from .args import options
from .measures import loadMdata
from .export import exportResults

# Supress pandas performance warnings
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)


def main():
    fname = "cli"
    description = "Cfpdes model"
    epilog = (
        "Setup for Magnet or Site simulation\n"
        "Workflow: actually fix current and compute cooling BCs using selected heatcorrelation\n"
        "\n"
        "Before running you need a flow_params for each magnet\n"
    )

    parser = options(description, epilog)
    args = parser.parse_args()
    args.cfgfile = os.path.abspath(args.cfgfile)
    args.wd = os.path.abspath(args.wd)

    pwd = os.getcwd()
    if args.wd != pwd:
        print(f"change working directory to {args.wd}", flush=True)
        os.chdir(args.wd)

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
        if not os.path.isabs(jsonmodel):
            jsonmodel = os.path.abspath(os.path.join(args.wd, jsonmodel))

        meshmodel = feelpp_config["cfpdes"]["mesh.filename"]
        if meshmodel.startswith("$cfgdir/"):
            meshmodel = meshmodel.replace(r"$cfgdir/", f"{basedir}/")
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

    if args.mdata:
        targets, postvalues = loadMdata(e, args.wd, args, targets, postvalues)

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
