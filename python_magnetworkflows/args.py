"""
Argparse definitions for the magnetworkflows CLI.
"""

import argparse
import json


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
        choices=["mean", "grad", "meanH", "gradH", "gradHZ", "gradHZH"],
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
