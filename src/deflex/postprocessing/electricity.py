# -*- coding: utf-8 -*-

"""
Analyses of the electricity sector. These function may work with multi-sectoral
scenarios as well, but one has to consider the effects on the results.

If there are chp plants in the system for example the results might be
distorted.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import pandas as pd
from oemof import solph
from pandas.testing import assert_frame_equal


def merit_order_from_scenario(
    scenario, with_downtime=True, with_co2_price=True
):
    """
    Create a merit order from a deflex scenario.

    TODO: Check transmission.
    TODO: Add volatile sources as an optional feature
    TODO: Check chp. Warn if chp are present. Add chp as an option
    TODO: Or warn if no chp are present, installed capacity might be too high

    Parameters
    ----------
    scenario : deflex.Scenario
        Path of the directory where the csv files of the scenario are located.
    with_downtime : bool
        Use down time factor to reduce the installed capacity.
    with_co2_price : bool
        Consider the CO2 price to calculate the merit order.

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> import os
    >>> from deflex import DeflexScenario
    >>> from deflex.tools import TEST_PATH
    >>> my_path = os.path.join(TEST_PATH, "de02_no-heat_csv")
    >>> sc = DeflexScenario()
    >>> mo1 = merit_order_from_scenario(sc.read_csv(my_path))
    >>> round(mo1.capacity_cum.iloc[-1], 4)
    86.7028
    >>> round(mo1.capacity.sum(), 1)
    86702.8
    >>> round(mo1.loc[("DE01", "natural gas - 0.55"), "costs_total"], 2)
    49.37
    >>> mo2 = merit_order_from_scenario(sc.read_csv(my_path),
    ...                                 with_downtime=False)
    >>> int(round(mo2.capacity.sum(), 0))
    101405
    >>> mo3 = merit_order_from_scenario(sc.read_csv(my_path),
    ...                                 with_co2_price=False)
    >>> round(mo3.loc[("DE01", "natural gas - 0.55"), "costs_total"], 2)
    43.58

    """
    sc = scenario
    sc.name = sc.input_data["general"].get("name")
    transf = sc.input_data["power plants"]
    num_cols = ["capacity", "variable_costs", "efficiency", "count"]
    transf[num_cols] = transf[num_cols].astype(float)
    if with_downtime and "downtime_factor" in transf:
        transf["capacity"] *= 1 - pd.to_numeric(
            transf["downtime_factor"].fillna(0.1)
        )
    transf = transf.loc[transf["capacity"] != 0]
    my_data = sc.input_data["commodity sources"].loc["DE"]
    my_data["co2_price"] = float(sc.input_data["general"].get("co2 price", 0))
    transf = transf.merge(
        my_data, right_index=True, how="left", left_on="fuel"
    )
    transf.rename(columns={"emission": "fuel_emission"}, inplace=True)
    transf["spec_emission"] = transf["fuel_emission"].div(transf["efficiency"])
    transf["costs_total"] = pd.to_numeric(
        transf["variable_costs"].fillna(1)
    ) + transf["costs"].div(transf["efficiency"])
    if with_co2_price and "co2_price" in transf:
        transf["costs_total"] += transf["co2_price"] * transf[
            "fuel_emission"
        ].div(transf["efficiency"])

    transf.sort_values(["costs_total", "capacity"], inplace=True)
    transf["capacity_cum"] = transf.capacity.cumsum().div(1000)
    return transf


def get_line_inflows(result):
    return [
        x
        for x in result["Main"].keys()
        if isinstance(x[1], solph.Bus)
        and x[1].label.cat == "electricity"
        and not x[0].label.cat == "line"
    ]


def merit_order_from_results(result):
    """
    Create a merit order from deflex results.

    Parameters
    ----------
    result : dict
        A deflex results dictionary.

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> from deflex import tools, postprocessing
    >>> fn = tools.fetch_test_files("de02_no-heat.dflx")
    >>> my_results = postprocessing.restore_results(fn)
    >>> a = merit_order_from_results(my_results)
    """
    # TODO: If there is a transmission limit or transmission losses
    #       the merit order cannot be calculated!!!!

    # Fetch all flows into any electricity bus
    inflows = get_line_inflows(result)

    # Create a DataFrame for the costs
    levels = [[], [], [], []]
    values = pd.DataFrame(index=pd.MultiIndex(levels=levels, codes=levels))
    for inflow in inflows:
        label = inflow[0].label

        component = inflow[0]
        electricity_bus = inflow[1]

        # Variable costs of the outflow of the component
        values.loc[label, "variable_costs_out"] = result["Param"][inflow][
            "scalars"
        ].variable_costs

        # Capacity of the component
        values.loc[label, "capacity"] = result["Param"][inflow]["scalars"].get(
            "nominal_value", 10000
        )

        srcbus2component = [
            x
            for x in result["Main"].keys()
            if x[1] == component and x[0] != electricity_bus
        ]

        if len(srcbus2component) > 0:
            srcbus = srcbus2component[0][0]
            # Variable costs of the inflow of the component
            values.loc[label, "variable_costs_in"] = result["Param"][
                srcbus2component[0]
            ]["scalars"].variable_costs

            # Efficiency of the component if component is a transformer.
            parameter_name = "conversion_factors_{0}".format(electricity_bus)
            values.loc[label, "efficiency"] = result["Param"][
                (component, None)
            ]["scalars"][parameter_name]

            src2srcbus = [
                x
                for x in result["Main"].keys()
                if x[1] == srcbus and x[0].label.cat != "shortage"
            ]
            if len(src2srcbus) > 1:
                msg = (
                    "More than one source found for {0}. "
                    "Source costs will be ambiguous."
                )
                raise ValueError(msg.format(srcbus))

            # Variable costs of the fuel source.
            values.loc[label, "fuel_costs"] = result["Param"][src2srcbus[0]][
                "scalars"
            ].variable_costs
            values.loc[label, "fuel_emission"] = result["Param"][
                src2srcbus[0]
            ]["scalars"].emission
            values.loc[label, "fuel"] = src2srcbus[0][0].label.subtag.replace(
                "_", " "
            )
            values.loc[label, "spec_emission"] = (
                values.loc[label, "fuel_emission"]
                / values.loc[label, "efficiency"]
            )
        else:
            values.loc[label, "efficiency"] = 1
            values.loc[label, "variable_costs_in"] = 0
            values.loc[label, "fuel_costs"] = 0
            values.loc[label, "fuel_emission"] = 0
            values.loc[label, "fuel"] = "no fuel"

        values.loc[label, "costs_total"] = (
            values.loc[label, "variable_costs_out"]
            + (
                values.loc[label, "variable_costs_in"]
                + values.loc[label, "fuel_costs"]
            )
            / values.loc[label, "efficiency"]
        )
    values = values.loc[values["fuel"] != "no fuel"]
    values.sort_values(["costs_total", "capacity"], inplace=True)
    values["capacity_cum"] = values.capacity.cumsum().div(1000)
    return values


def check_comparision_of_merit_order(scenario):
    """Comparison of two different ways to calculate the merit order.

    1. Calculate the merit order from scenario
    2. Calculate the merit order from the results

    The resulting tables are not exactly the same because they will have some
    additional columns. The following columns should be the same.

    "capacity", "efficiency", "fuel_emission", "fuel", "costs_total",
    "capacity_cum"

    Parameters
    ----------
    scenario : deflex.Scenario
        Full path of results file.

    Examples
    --------
    >>> from deflex import tools, scenario
    >>> my_path = tools.fetch_test_files("de02_no-heat.dflx")
    >>> sc = scenario.restore_scenario(my_path)
    >>> check_comparision_of_merit_order(sc)
    Check passed! Both merit order DataFrame tables are the same.
    """
    mo_scenario = merit_order_from_scenario(scenario)
    mo_results = merit_order_from_results(scenario.results)

    mo_results.index = mo_scenario.index

    compare_columns = [
        "capacity",
        "efficiency",
        "fuel_emission",
        "spec_emission",
        "fuel",
        "costs_total",
        "capacity_cum",
    ]
    assert_frame_equal(
        mo_scenario[compare_columns], mo_results[compare_columns]
    )
    print("Check passed! Both merit order DataFrame tables are the same.")
