# -*- coding: utf-8 -*-

"""Basic result processing.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

__all__ = [
    "get_all_results",
    "DeflexGraph",
]

import networkx as nx
import pandas as pd
from matplotlib.cm import get_cmap
from matplotlib.colors import Normalize, rgb2hex
from oemof import solph


def get_time_index(results):
    key = list(results["main"].keys())[0]
    return results["main"][key]["sequences"].index


def meta_results2series(results):
    meta = results["Meta"]
    meta.pop("solver")
    meta.pop("problem")
    return pd.Series(meta)


def pyomo_results2series(results):
    pyomo = pd.Series(
        index=pd.MultiIndex(levels=[[], []], codes=[[], []]), dtype="object"
    )
    for k, v in dict(results["Solver"][0]).items():
        try:
            pyomo["Solver", k] = v.value
        except AttributeError:
            for k2, v2 in dict(results["Solver"][0][k]).items():
                for k3, v3 in dict(results["Solver"][0][k][k2]).items():
                    pyomo["Solver " + k2, k3] = v3.value
    for k, v in dict(results["Problem"][0]).items():
        pyomo["Problem", k] = v.value

    for k, v in results["Solution"].items():
        pyomo["Solution", k] = v.value
    return pyomo.sort_index()


def components2table(results):
    classes = {
        solph.GenericStorage: "storage",
        solph.custom.SinkDSM: "demand response",
    }

    comp_results = {}
    for cls in classes.keys():
        components = [
            k[0] for k in results["main"].keys() if isinstance(k[0], cls)
        ]
        components.extend(
            [k[1] for k in results["main"].keys() if isinstance(k[1], cls)]
        )
        components = set(components)

        levels = [[], [], [], [], []]
        seq = pd.DataFrame(columns=pd.MultiIndex(levels=levels, codes=levels))
        for component in components:
            for col in results["main"][component, None]["sequences"].columns:
                seq[
                    component.label.cat,
                    component.label.tag,
                    component.label.subtag,
                    component.label.region,
                    col,
                ] = results["main"][component, None]["sequences"][col]
        if len(seq) > 0:
            comp_results[classes[cls]] = seq
    return comp_results


def bus_flows2tables(results, bus_groups):
    levels = [[], [], [], [], [], [], [], []]
    tables = {}
    for key, buses in bus_groups.items():
        seq = pd.DataFrame(columns=pd.MultiIndex(levels=levels, codes=levels))
        name = "_".join(key).replace("_all", "")
        for bus in buses:
            flows = [k for k in results["main"].keys() if k[1] == bus]
            flows.extend([k for k in results["main"].keys() if k[0] == bus])
            for f in flows:
                seq[
                    f[0].label.cat,
                    f[0].label.tag,
                    f[0].label.subtag,
                    f[0].label.region,
                    f[1].label.cat,
                    f[1].label.tag,
                    f[1].label.subtag,
                    f[1].label.region,
                ] = results["main"][f]["sequences"]["flow"]
        tables[name] = seq.sort_index(axis=1)

    return tables


def group_buses(buses, fields):
    groups = {}
    for b in buses:
        temp = []
        for field in fields:
            temp.append(getattr(b.label, field))
        if tuple(temp) in groups.keys():
            groups[tuple(temp)].append(b)
        else:
            groups[tuple(temp)] = [b]
    return groups


def get_all_results(results):
    """
    SOMETHING

    Parameters
    ----------
    results

    Returns
    -------

    Examples
    --------
    >>> import os
    >>> from deflex.tools import restore_results, dict2file
    >>> from deflex.tools import fetch_test_files
    >>> fn = fetch_test_files("de03_fictive.dflx")
    >>> my_results = restore_results(fn)
    >>> all_results = get_all_results(my_results)
    >>> sorted(list(all_results.keys()))[:4]
    ['commodity', 'electricity', 'heat_decentralised', 'heat_district']
    >>> sorted(list(all_results.keys()))[-5:]
    ['heat_district', 'meta', 'mobility', 'pyomo', 'storages']
    >>> fn_out = fn.replace(".dflx", "_all_results.csv")
    >>> dict2file(all_results, fn_out, "csv", drop_empty_columns=True)
    >>> my_bool = []
    >>> for key in all_results.keys():
    ...     fn_test = os.path.join(fn_out, key + ".csv")
    ...     my_bool.append(os.path.isfile(fn_test))
    >>> my_bool
    [True, True, True, True, True, True, True, True]
    """
    buses = set(
        [k[0] for k in results["main"].keys() if isinstance(k[0], solph.Bus)]
    )
    bus_groups = group_buses(buses, ["cat", "tag"])
    tables = bus_flows2tables(results, bus_groups)
    tables.update(components2table(results))
    tables["pyomo"] = pyomo_results2series(results)
    tables["meta"] = meta_results2series(results)
    return tables
