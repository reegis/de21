# -*- coding: utf-8 -*-

"""
General deflex analyses.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import operator
from collections import namedtuple
from functools import reduce

import pandas as pd
from networkx import simple_cycles
from oemof import solph

from deflex.postprocessing import DeflexGraph
from deflex.tools import allocate_fuel

# 1. fetch_cycles: return all cycles with time series
# -> DF mit from, to im Index und dann zwei Spalten flow, cf, und eine
# künstliche Zwischenspalte für den nächsten, damit alle Untereinander stehen.
# Dann noch eine Info ob es ein theoretischer Kreis, ein wirklich genutzter
# Kreis oder sogar ein kritischer Kreis (innerhalb eines Zeitschritts ist.
# 2a. detect_cycles: find real cycles (all flow sums > 0)
# 2b. detect_cycles: find time step cylces (all flows > 0 within a time step)
# !!!2b should be False for all cycles.
# 3. fetch_bus_cycle: Ein Bus wird übergeben und wenn der Bus in einem Kreis außer line/storage ist dann wird die Kreisbilanz zurückgegeben. Wieviel wurde in den Kreis gegeben und wieviel geholt. Das kann das verechnet werden.


def detect_cycles(results):
    cycles = namedtuple("GraphCycles", ["storages", "line", "other"])
    dflx_graph = DeflexGraph(results)
    s_cycles = simple_cycles(dflx_graph.get())
    t_flows = [
        f for f in results["main"] if isinstance(f[0], solph.Transformer)
    ]
    buses = set([f[0] for f in results["main"] if isinstance(f[0], solph.Bus)])
    e_buses = [b.label for b in buses if b.label.cat == "electricity"]
    for bus in e_buses:
        print(repr(bus))
    # for tf in t_flows:
    #     # print(results["param"][(tf[0], None)])
    #     # print(results["param"][tf])
    #     print(tf[0])
    #     for k in tf[0].conversion_factors.keys():
    #         if k == tf[1]:
    #             print("Key exists")
    #             print(hash(k) == hash(tf[1]))
    #     if tf[1] in tf[0].conversion_factors:
    #         print("Key in keys")
    #     else:
    #         print("Key not in keys")
    #     print(hash(tf[1]))
    #     print("*********************next step")
    #     # print(tf[0].conversion_factors[tf[1]][0])
    # exit(0)
    flows = [k for k in results["main"].keys() if k[1] is not None]
    cvf = list()
    for c in s_cycles:
        # print(set(c))
        # print(set(e_buses))
        print(set(c).intersection(set(e_buses)))
        print("######################")
        if "cat='storage'" not in str(c) and "cat='line'" not in str(c):
            # if 1 == 1:
            # print(c)
            if len(set(c).intersection(set(e_buses))) > 0:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            for a in range(len(c)):
                flow = [
                    f
                    for f in flows
                    if (f[0].label, f[1].label) == (c[a - 1], c[a])
                ][0]
                if getattr(flow[0], "conversion_factors", None) is not None:
                    print("******", flow[0], "********")
                    inflow = [
                        k for k in results["main"].keys() if k[1] == flow[0]
                    ][0]
                    print(results["main"][inflow]["sequences"]["flow"].sum())
                    temp = results["param"][(flow[0], None)]["scalars"][
                        "conversion_factors_{0}".format(flow[1])
                    ]
                    print(temp)
                    cvf.append(temp)
                    print(results["main"][flow]["sequences"]["flow"].sum())
    print(reduce(operator.mul, cvf, 1))


def get_all_nodes_from_results(results):
    keys = sorted(list(results["main"].keys()))
    unique_nodes = []
    for nodes in keys:
        unique_nodes.append(nodes[0])
        if nodes[1] is not None:
            unique_nodes.append(nodes[1])
    return set(unique_nodes)


def nodes2table(results):
    """
    Get a table with all nodes (class, category, tag, subtag, region) from a
    results dictionary.

    Parameters
    ----------
    results : dict

    Returns
    -------
    Table with all nodes : pandas.DataFrame

    Examples
    --------
    >>> from deflex import tools
    >>> from deflex import postprocessing
    >>> fn = tools.fetch_test_files("de03_fictive.dflx")
    >>> my_results = postprocessing.restore_results(fn)
    >>> all_nodes = nodes2table(my_results)
    >>> len(all_nodes)
    238
    >>> all_nodes.to_csv("your/path/file.csv")  # doctest: +SKIP


    """
    unique_nodes = get_all_nodes_from_results(results)
    df = pd.DataFrame()
    n = 0
    for node in unique_nodes:
        solph_class = type(node)
        label = node.label
        n += 1
        df.loc[n, "class"] = str(solph_class).split(".")[-1].replace("'>", "")
        df.loc[n, "cat"] = label.cat
        df.loc[n, "tag"] = label.tag
        df.loc[n, "subtag"] = label.subtag
        df.loc[n, "region"] = label.region
    df.sort_values(by=list(df.columns), inplace=True)
    return df.reset_index(drop=True)


def fetch_converter_with_in_out_flows(results):
    # Select all converters (class Transformer excluding lines)
    transformer_objects = set(
        [
            k[0]
            for k in results["main"].keys()
            if isinstance(k[0], solph.Transformer) and k[0].label.cat != "line"
        ]
    )

    # Create dictionary with all converters and their in- and outflows.
    converter = {}
    for t in transformer_objects:
        converter[t] = {}
        converter[t]["in"] = {}
        converter[t]["out"] = {}

        inflow = [k for k in results["main"].keys() if k[1] == t][0]
        sector = inflow[0].label.subtag
        if sector == "all":
            key = (inflow[0].label.cat, inflow[0].label.region)
        else:
            key = (sector, inflow[0].label.region)
        converter[t]["in"][key] = inflow

        outflows = [k for k in results["main"].keys() if k[0] == t]
        for outflow in outflows:
            converter[t]["out"][
                (outflow[1].label.cat, outflow[1].label.region)
            ] = outflow

    return converter


def get_time_index(results):
    key = list(results["main"].keys())[0]
    return results["main"][key]["sequences"].index


def fetch_parameter_of_commodity_sources(results):
    commodity_sources = [
        k
        for k in results["main"].keys()
        if isinstance(k[0], solph.Source)
        and k[0].label.tag == "commodity"
        and k[0].label.cat != "shortage"
    ]

    parameter = pd.DataFrame(
        index=pd.MultiIndex(levels=[[], []], codes=[[], []])
    )
    for c in commodity_sources:
        for k, v in results["param"][c]["scalars"].items():
            if k != "label":
                parameter.loc[(c[0].label.subtag, c[0].label.region), k] = v
    return parameter


def fetch_volatile_electricity_sources(results):
    """

    Parameters
    ----------
    results

    Returns
    -------
    pandas.DataFrame

    """
    volatile_sources = [
        k
        for k in results["main"].keys()
        if isinstance(k[0], solph.Source) and k[0].label.tag == "volatile"
    ]
    sources = pd.DataFrame(
        columns=pd.MultiIndex(levels=[[], []], codes=[[], []])
    )

    for src in volatile_sources:
        sources[src[0].label.subtag, src[0].label.region] = results["main"][
            src
        ]["sequences"]["flow"]
    return sources


def _calculate_emissions_from_energy_table(table, emissions):
    emission_table = table["in"].mul(emissions)
    emission_table = pd.concat([emission_table], axis=1, keys=["in"])
    emission_table["out", "electricity"] = emission_table["in"].sum(axis=1)
    # exit(0)
    table = pd.concat(
        [table, emission_table],
        axis=1,
        keys=["energy", "emission"],
    )
    return table.sort_index(axis=1)


def calculate_product_fuel_balance(results, chp_method, **kwargs):
    transformer = fetch_converter_with_in_out_flows(results)

    # Create a dictionary of empty tables (pandas.DataFrame) for all sectors
    tables = {}
    mcol = pd.MultiIndex(levels=[[], []], codes=[[], []])
    time_index = get_time_index(results)
    for t, f in transformer.items():
        for k1 in f["out"].keys():
            tables.setdefault(
                k1[0], pd.DataFrame(columns=mcol, index=time_index)
            )
            tables[k1[0]]["out", k1] = 0
            for k2 in f["in"].keys():
                tables[k1[0]]["in", k2] = 0

    # Assign inflows to cumulated product flows (fill empty tables from above)
    for t, f in transformer.items():
        if len(f["out"]) == 1:
            fuel_factors = None
        else:
            fuel_factors = allocate_fuel(method=chp_method, **kwargs)

        for sector, outflow in f["out"].items():
            tables[sector[0]]["out", sector] += results["main"][outflow][
                "sequences"
            ]["flow"]
            for fuel, inflow in f["in"].items():
                tables[sector[0]]["in", fuel] += results["main"][inflow][
                    "sequences"
                ]["flow"] * getattr(fuel_factors, sector[0], 1)

    # Add volatile source to electricity table
    volatile_output_by_region = (
        fetch_volatile_electricity_sources(results)
        .groupby(level=1, axis=1)
        .sum()
    )

    for region in volatile_output_by_region.columns:
        if ("out", ("electricity", region)) in tables["electricity"]:
            tables["electricity"][
                "out", ("electricity", region)
            ] += volatile_output_by_region[region]
        else:
            tables["electricity"][
                "out", ("electricity", region)
            ] = volatile_output_by_region[region]

    dict2file(tables, "/home/uwe/000aatemp.xlsx", "xlsx")
    exit(0)

    emissions = fetch_parameter_of_commodity_sources(results)["emission"]
    emissions.index = emissions.index.to_flat_index()
    emission_series = (
        pd.DataFrame(index=time_index, columns=emissions.index)
        .fillna(1)
        .mul(emissions)
    )

    tables["electricity"] = _calculate_emissions_from_energy_table(
        tables["electricity"], emission_series
    )

    last_key = None
    for column in tables["electricity"]["energy", "out"].columns:
        emission_series[("electricity", column[1])] = tables["electricity"][
            "emission", "out", "electricity"
        ] / tables["electricity"]["energy", "out"].sum(axis=1)
        last_key = column[1]

    avg_elec_emissions = (
        tables["electricity"]["emission", "out", "electricity"].sum()
        / tables["electricity"]["energy", "out"].sum().sum()
    )
    emissions = emissions.append(
        pd.Series({("electricity", "all"): avg_elec_emissions})
    )
    sectors = [k for k in tables.keys() if k != "electricity"]

    for sector in sectors:
        tables[sector] = _calculate_emissions_from_energy_table(
            tables[sector], emissions
        )

    tables["emissions"] = emissions.reindex(emissions.index)
    tables["electricity emission series"] = emission_series[
        ("electricity", last_key)
    ]
    return tables


if __name__ == "__main__":
    # pass
    from deflex.tools import dict2file, restore_results

    # import os
    #
    # allocate_fuel("finnish", eta_e=0.3, eta_th=0.5)
    # # print(finnish_method(0.3, 0.5, 0.5, 0.9))
    # exit(0)
    my_fn = "/home/uwe/.deflex/pedro/2030-DE02-Agora9.dflx"
    # # fn = os.path.join(
    # #     os.path.expanduser("~"),
    # #     ".deflex",
    # #     "tmp_test_32traffic_43",
    # #     "results_cbc",
    # #     "de03_fictive.dflx",
    # # )
    #
    my_results = restore_results(my_fn)
    #
    # # filename1 = fn.replace(".dflx", "_results.xlsx")
    # # all_results = get_all_results(my_results)
    # # dict2file(all_results, filename1)
    #
    filename2 = my_fn.replace(".dflx", "_results_emission.xlsx")
    my_tables = calculate_product_fuel_balance(
        my_results,
        "finnish",
        eta_e=0.3,
        eta_th=0.5,
        eta_e_ref=0.5,
        eta_th_ref=0.9,
    )
    dict2file(my_tables, filename2, drop_empty_columns=True)
    # # for table in all_results._fields:
    # #     print("\n\n***************** " + table + " ****************\n")
    # #     print(getattr(all_results, table))
