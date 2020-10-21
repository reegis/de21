# -*- coding: utf-8 -*-

"""Main script.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging
from datetime import datetime
import time
import traceback

# internal modules
from deflex import config as cfg
from deflex import scenario_tools


def stopwatch():
    """Track the running time."""
    if not hasattr(stopwatch, "start"):
        stopwatch.start = datetime.now()
    return str(datetime.now() - stopwatch.start)[:-7]


def main_secure(year, rmap, csv=True, es=None, plot_graph=False,
                extra_regions=None):
    """

    Parameters
    ----------
    ----------
    year : int
        Year of an existing  basic scenario.
    rmap : str
        A valid deflex map id (de02, de17, de21, de22) of an existing scenario.
    csv : bool
        Use csv collection. If set to False the xls-file is used.
    es : oemof.solph.EnergySystem
        A valid energy system if needed.
    plot_graph : bool
        Set to True to plot the energy system.
    extra_regions : list
        Use separate resource buses for these regions.

    Returns
    -------

    Examples
    --------
    >>> main_secure(2014, 'de21')  # doctest: +SKIP
    """
    try:
        main(year, rmap, csv=csv, es=es, plot_graph=plot_graph,
             extra_regions=extra_regions)
    except Exception as e:
        logging.error(traceback.format_exc())
        time.sleep(0.5)
        logging.error(e)
        time.sleep(0.5)


def main(year, rmap, csv=True, es=None, plot_graph=False, extra_regions=None):
    """

    Parameters
    ----------
    year : int
        Year of an existing  basic scenario.
    rmap : str
        A valid deflex map id (de02, de17, de21, de22) of an existing scenario.
    csv : bool
        Use csv collection. If set to False the xls-file is used.
    es : oemof.solph.EnergySystem
        A valid energy system if needed.
    plot_graph : bool
        Set to True to plot the energy system.
    extra_regions : list
        Use separate resource buses for these regions.

    Returns
    -------

    Examples
    --------
    >>> main(2014, 'de21')  # doctest: +SKIP
    """
    stopwatch()
    cfg.tmp_set("init", "map", rmap)
    name = "{0}_{1}_{2}".format("deflex", year, cfg.get("init", "map"))

    path = os.path.join(cfg.get("paths", "scenario"), "deflex", str(year))

    if csv is True:
        csv_dir = name + "_csv"
        csv_path = os.path.join(path, csv_dir)
        excel_path = None
    else:
        excel_path = os.path.join(path, name + ".xls")
        csv_path = None

    model_scenario(
        xls_file=excel_path,
        csv_path=csv_path,
        res_path=path,
        name=name,
        rmap=rmap,
        year=year,
        es=es,
        plot_graph=plot_graph,
        extra_regions=extra_regions,
    )


def model_scenario(
    xls_file=None,
    csv_path=None,
    res_path=None,
    name="noname",
    rmap=None,
    year="unknown",
    es=None,
    plot_graph=False,
    extra_regions=None,
):
    """
    Compute a deflex scenario.

    Parameters
    ----------
    xls_file : str
        Full filename to a valid xls-file.
    csv_path : str
        Full path to a valid csv-collection.
    res_path : str
        Path to store the output file. If None the results will be stored along
        with the scenarios.
    name : str
        The name of the scenario.
    year : int
        The year or year-range of the scenario.
    rmap : str
        The name of the used region map.
    es : oemof.solph.EnergySystem
        A valid energy system if needed.
    plot_graph : bool
        Set to True to plot the energy system.
    extra_regions : list
        Use separate resource buses for these regions.

    Returns
    -------

    Examples
    --------
    >>> model_scenario('/my/path/to/scenario.xls', name='my_scenario',
    ...                rmap='deXX', year=2025)  # doctest: +SKIP
    """
    stopwatch()

    if xls_file is not None and csv_path is not None:
        raise ValueError("It is not allowed to define more than one input.")

    meta = {
        "year": year,
        "model_base": "deflex",
        "map": rmap,
        "solver": cfg.get("general", "solver"),
        "start_time": datetime.now(),
    }

    sc = scenario_tools.DeflexScenario(name=name, year=2014, meta=meta)
    if es is not None:
        sc.es = es

    if csv_path is not None:
        if res_path is None:
            res_path = os.path.dirname(csv_path)
        logging.info(
            "Read scenario from csv collection: {0}".format(stopwatch())
        )
        sc.load_csv(csv_path)
    elif xls_file is not None:
        if res_path is None:
            res_path = os.path.dirname(xls_file)
        logging.info("Read scenario from xls-file: {0}".format(stopwatch()))
        sc.load_excel(xls_file)

    if extra_regions is not None:
        sc.extra_regions = extra_regions

    logging.info("Add nodes to the EnergySystem: {0}".format(stopwatch()))
    sc.table2es()

    # Save energySystem to '.graphml' file if plot_graph is True
    if plot_graph:
        sc.plot_nodes(
            filename=os.path.join(res_path, name),
            remove_nodes_with_substrings=["bus_cs"],
        )

    logging.info("Create the concrete model: {0}".format(stopwatch()))
    sc.create_model()

    logging.info("Solve the optimisation model: {0}".format(stopwatch()))
    sc.solve(solver=cfg.get("general", "solver"))

    logging.info("Solved. Dump results: {0}".format(stopwatch()))
    res_path = os.path.join(
        res_path, "results_{0}".format(cfg.get("general", "solver"))
    )
    os.makedirs(res_path, exist_ok=True)
    out_file = os.path.join(res_path, name + ".esys")
    logging.info("Dump file to {0}".format(out_file))
    sc.meta["end_time"] = datetime.now()
    sc.dump_es(out_file)

    logging.info(
        "All done. deflex finished without errors: {0}".format(stopwatch())
    )


if __name__ == "__main__":
    fn_xls = "/home/uwe/reegis/phd/deflex_2014_de21.xls"
    fn_csv = "/home/uwe/reegis/phd/deflex_2014_de21_csv"
    sc = scenario_tools.DeflexScenario()
    # sc.load_excel(fn_xls)
    sc.load_csv(fn_csv)
