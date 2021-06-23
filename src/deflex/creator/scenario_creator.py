# -*- coding: utf-8 -*-

"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""


import json
import logging
import os
from collections import namedtuple

import pandas as pd
from reegis import config
from scenario_builder import (
    commodity,
    demand,
    feedin,
    mobility,
    powerplants,
    storages,
)

from deflex import __file__ as dfile
from deflex import config as cfg
from deflex import scenario
from deflex.creator import transmission


def scenario_default_decentralised_heat():
    """

    Returns
    -------

    """
    df = pd.DataFrame(index=pd.MultiIndex(levels=[[], []], codes=[[], []]))
    fuels = [
        ("gas", "natural gas"),
        ("hard coal", "hard coal"),
        ("lignite", "lignite"),
        ("natural gas", "natural gas"),
        ("oil", "oil"),
        ("other", "other"),
        ("re", "other"),
    ]
    for fuel, source in fuels:
        df.loc[("DE", fuel), "efficiency"] = 0.85
        df.loc[("DE", fuel), "source"] = source

    df["source region"] = "DE"

    return df


def create_scenario(regions, year, name, lines, opsd_version=None):
    """

    Parameters
    ----------
    regions
    year
    name
    lines : iterable[str]
        A list of names of transmission lines. All name must contain a dash
        between the id of the regions (FromRegion-ToRegion).
    opsd_version

    Returns
    -------

    """
    if opsd_version is None:
        if year < 2015:
            opsd_version = "2019-06-05"

    table_collection = {"general": pd.DataFrame()}

    logging.info("BASIC SCENARIO - STORAGES")
    table_collection["electricity storages"] = storages.scenario_storages(
        regions, year, name
    )

    logging.info("BASIC SCENARIO - POWER PLANTS")
    pp = powerplants.scenario_powerplants(
        table_collection, regions, year, name
    )
    table_collection["volatile plants"] = pp["volatile plants"]
    table_collection["power plants"] = pp["power plants"]

    logging.info("BASIC SCENARIO - TRANSMISSION")
    if len(regions) > 1:
        table_collection["power lines"] = transmission.scenario_transmission(
            regions, lines
        )
    else:
        logging.info("...skipped")

    logging.info("BASIC SCENARIO - CHP PLANTS")
    if cfg.get("creator", "heat"):
        chp = powerplants.scenario_chp(table_collection, regions, year, name)
        table_collection["heat-chp plants"] = chp["heat-chp plants"]
        table_collection["power plants"] = chp["power plants"]
    else:
        logging.info("...skipped")

    logging.info("BASIC SCENARIO - DECENTRALISED HEAT")
    if cfg.get("creator", "heat"):
        table_collection[
            "decentralised heat"
        ] = scenario_default_decentralised_heat()
    else:
        logging.info("...skipped")

    logging.info("BASIC SCENARIO - SOURCES")
    cs = commodity.scenario_commodity_sources(year)
    table_collection["general"].loc["co2 price", "value"] = cs.pop(
        "co2_price"
    ).iloc[0]
    cs["emission"] /= 1000
    table_collection["commodity sources"] = cs
    table_collection["volatile series"] = feedin.scenario_feedin(
        regions, year, name
    )

    logging.info("BASIC SCENARIO - DEMAND")
    table_collection.update(
        demand.scenario_demand(
            regions,
            year,
            name,
            opsd_version=opsd_version,
        )
    )

    logging.info("BASIC SCENARIO - MOBILITY")
    if cfg.get("creator", "mobility"):
        table_collection = mobility.scenario_mobility(year, table_collection)
    else:
        logging.info("...skipped")

    logging.info("ADD GENERAL DATA")
    table_collection["general"] = pd.concat(
        [table_collection["general"], general_data(year, table_collection)]
    )
    table_collection["info"] = meta_data()
    logging.info("ADD META DATA")
    return table_collection


def general_data(year, input_data):
    general = pd.DataFrame(columns=["value"])
    general.loc["year"] = year
    general.loc["number of time steps"] = len(
        input_data["electricity demand series"]
    )

    # Create name
    if cfg.get("creator", "heat"):
        heat = "heat"
    else:
        heat = "no-heat"
    if cfg.get("creator", "group_transformer"):
        merit = "no-reg-merit"
    else:
        merit = "reg-merit"
    general.loc["name"] = "{0}_{1}_{2}_{3}_{4}".format(
        "deflex", year, cfg.get("creator", "map"), heat, merit
    )
    return general


def meta_data():
    meta = pd.DataFrame.from_dict(
        cfg.get_dict("creator"), orient="index", columns=["value"]
    )
    meta.loc["map"] = cfg.get("creator", "map")
    return meta


def clean_time_series(table_collection):
    """

    Parameters
    ----------
    table_collection

    Returns
    -------

    """
    series = [t for t in table_collection.keys() if "series" in t]

    vts = table_collection["volatile series"]
    vp = table_collection["volatile plants"]

    for key in series:
        for column, data in table_collection[key].items():
            if data.sum() == 0:
                msg = (
                    "Removing column %s of table %s because"
                    "sum of column is %s"
                )
                logging.debug(msg, column, key, data.sum())
                del table_collection[key][column]

    for index, data in table_collection["volatile series"].items():
        if index in vp.index:
            if vp.loc[index, "capacity"] == 0:
                remove = True
                msg = (
                    "Removing volatile series: %s  "
                    "because installed capacity is %s"
                )
                logging.debug(msg, index, vp.loc[index])
            else:
                remove = False
        else:
            remove = True
            msg = (
                "Removing volatile series: %s  "
                "because installed capacity does not exist."
            )
            logging.debug(msg, index)
        if remove is True:
            vts.drop(index, axis=1, inplace=True)

    for index, data in table_collection["power plants"].iterrows():
        if data["capacity"] == 0:
            table_collection["power plants"].drop(index, axis=0, inplace=True)

    return table_collection


def create_basic_reegis_scenario(
    name,
    regions,
    parameter,
    lines=None,
    csv_path=None,
    excel_path=None,
):
    """
    Create a basic scenario for a given year and region-set.

    Parameters
    ----------
    name : str
        Name of the scenario
    regions : geopandas.geoDataFrame
        Set of region polygons.
    lines : geopandas.geoDataFrame
        Set of transmission lines.
    parameter : dict
        Parameter set for the creation process. Some parameters will have a
        default value. For the default values see below.
    csv_path : str
        A directory to store the scenario as csv collection. If None no csv
        collection will be created. Either csv_path or excel_path must not be
        'None'.
    excel_path : str
        A file to store the scenario as an excel map. If None no excel file
        will be created. Both suffixes 'xls' or 'xlsx' are possible. The excel
        format can be used in most spreadsheet programs such as LibreOffice or
        Gnumeric. Either csv_path or excel_path must not be 'None'.

    Returns
    -------
    namedtuple : Path

    Notes
    -----

    List of default values:

        * copperplate: True
        * default_transmission_efficiency: 0.9
        * costs_source: "ewi"
        * downtime_bioenergy: 0.1
        * group_transformer: False
        * heat: False
        * limited_transformer: "bioenergy",
        * local_fuels: "district heating",
        * map: "de02",
        * mobility_other: "petrol",
        * round: 1,
        * separate_heat_regions: "de22",
        * use_CO2_costs: False,
        * use_downtime_factor: True,
        * use_variable_costs: False,
        * year: 2014

    Examples
    --------
    >>> from oemof.tools import logger
    >>> from deflex.geometries import deflex_power_lines
    >>> from deflex.geometries import deflex_regions
    >>>
    >>> logger.define_logging(screen_level=logging.DEBUG)  # doctest: +SKIP
    >>>
    >>> my_parameter = {
    ...     "year": 2014,
    ...     "map": "de02",
    ...     "copperplate": True,
    ...     "heat": True,
    ... }
    >>>
    >>> my_name = "deflex"
    >>> for k, v in my_parameter.items():
    ...     my_name += "_" + str(k) + "-" + str(v)
    >>>
    >>> polygons = deflex_regions(rmap=my_parameter["map"], rtype="polygons")
    >>> my_lines = deflex_power_lines(my_parameter["map"]).index
    >>> path = "/my/path/creator/{0}{1}".format(my_name, "{0}")
    >>>
    >>> create_basic_reegis_scenario(
    ...     name=my_name,
    ...     regions=polygons,
    ...     lines=my_lines,
    ...     parameter=my_parameter,
    ...     excel_path=path.format(".xlsx"),
    ...     csv_path=path.format("_csv"),
    ... )  # doctest: +SKIP
    """
    # The default parameter can be found in "creator.ini".

    config.init(paths=[os.path.dirname(dfile)])
    for option, value in parameter.items():
        cfg.tmp_set("creator", option, str(value))
        config.tmp_set("creator", option, str(value))

    year = cfg.get("creator", "year")

    configuration = json.dumps(
        cfg.get_dict("creator"), indent=4, sort_keys=True
    )

    logging.info(
        "The following configuration is used to build the scenario:" " %s",
        configuration,
    )
    paths = namedtuple("paths", "xls, csv")

    table_collection = create_scenario(regions, year, name, lines)

    table_collection = clean_time_series(table_collection)

    name = table_collection["general"].get("name")
    sce = scenario.Scenario(input_data=table_collection, name=name, year=year)

    if csv_path is not None:
        os.makedirs(csv_path, exist_ok=True)
        sce.to_csv(csv_path)
    if excel_path is not None:
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)
        sce.to_xlsx(excel_path)

    return paths(xls=excel_path, csv=csv_path)
