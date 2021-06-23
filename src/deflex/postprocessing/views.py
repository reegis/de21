# -*- coding: utf-8 -*-

"""
General deflex analyses.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


import pandas as pd


def reshape_bus_view(results, buses, data=None, aggregate=None):
    """
    Create a MultiIndex DataFrame with all Flows around the Bus objects. The
    first column level contains ``'in'`` or ``'out'`` for ingoing and outgoing
    flows.


    Parameters
    ----------
    results: dict
        A solph results dictionary from a deflex scenario.
    buses : list[solph.Bus] or solph.Bus
        A single bus node or a list of buses.
    data : pandas.DataFrame
        MultiIndex DataFrame to add the results to.
    aggregate : list or None
        A list of tuples that will replace the subtag. The subtag normally
        divides similar nodes. The subtag of power plant nodes for example
        contains the used fuel, By replacing the fuel with a name such as "all"
        all power plants will be aggregated. The tuple must have three fields:
        (field to check, value of the field, new value of subtag)
        e.g. ("tag", "pp", "all") will change all power plants:
        trsf_pp_oil_DE02 -> trsf_pp_all_DE02
        trsf_pp_lignite_DE02 -> trsf_pp_all_DE02
        trsf_chp_oil_DE02 ->  trsf_chp_oil_DE02
        If the last field of the tuple is an integer the last (-1) or first (1)
        part of a subtag is removed
        e.g. ("tag", "pp", -1) will change all power plants:
        trsf_pp_oil_038_DE02 -> trsf_pp_oil_DE02
        trsf_pp_oil_039_DE02 -> trsf_pp_oil_DE02
        trsf_pp_lignite_035_DE02 ->  trsf_pp_lignite_DE02
        Nodes with the same label will be aggregated.

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> from oemof import solph
    >>> from deflex.tools import fetch_test_files
    >>> from deflex.postprocessing import restore_results
    >>> fn = fetch_test_files("de21_no-heat.dflx")
    >>> my_results = restore_results(fn)
    >>> my_buses = [flow[0] for flow in my_results["main"].keys() if
    ...             isinstance(flow[0], solph.Bus) and
    ...             flow[0].label.cat == "electricity"]
    >>> len(set(my_buses))
    21
    >>> # aggregate lines for all regions and remove suffix of power plants
    >>> agg = [("cat", "line", "subtag", "all"),
    ...        ("cat", "power plant", "tag", -1),
    ...        ("cat", "power plant", "subtag", "all")]
    >>> df1 = reshape_bus_view(my_results, my_buses, aggregate=agg)
    >>> df2 = reshape_bus_view(my_results, list(my_buses))
    >>> df1g1 = df1.groupby(level=[1, 2, 3, 4], axis=1).sum()
    >>> df2g1 = df2.groupby(level=[1, 2, 3, 4], axis=1).sum()
    >>> list(df1g1["in", "line", "electricity"].columns[:5])
    ['all']
    >>> list(df2g1["in", "line", "electricity"].columns[:5])
    ['DE01', 'DE02', 'DE03', 'DE04', 'DE05']
    >>> df1g2 = df1.groupby(level=[1, 2, 3], axis=1).sum()
    >>> df2g2 = df2.groupby(level=[1, 2, 3], axis=1).sum()
    >>> list(df1g2["in", "power plant"].columns[:4])
    ['bioenergy', 'hard coal', 'lignite', 'natural gas']
    >>> list(df2g2["in", "power plant"].columns[:4])
    ['bioenergy_038', 'bioenergy_042', 'bioenergy_045', 'hard coal_023']
    >>> int(df1.sum().sum())
    7529461
    >>> int(df2.sum().sum())
    7529461

    """
    if aggregate is None:
        aggregate = []
    if data is None:
        m_cols = pd.MultiIndex(
            levels=[[], [], [], [], []], codes=[[], [], [], [], []]
        )
        data = pd.DataFrame(columns=m_cols)

    if not isinstance(buses, list):
        buses = [buses]
    else:
        buses = list(set(buses))

    def change_field(node, changes):
        val = {"subtag": node.label.subtag, "tag": node.label.tag}
        for agg in changes:
            field = agg[2]
            if getattr(node.label, agg[0]) == agg[1]:
                if isinstance(agg[3], int):
                    if agg[3] < 0:
                        val[field] = "_".join(
                            getattr(node.label, field).split("_")[: agg[3]]
                        )
                    else:
                        val[field] = "_".join(
                            getattr(node.label, field).split("_")[agg[3] :]
                        )
                else:
                    val[field] = agg[3]
        return val

    for bus in buses:
        # filter all nodes and sub-list import/exports
        node_flows = [
            x
            for x in results["Main"].keys()
            if bus in (x[1], x[0]) and x[1] is not None
        ]

        # Add all flow time series to a MultiIndex DataFrame using in/out
        for flow in node_flows:
            if flow[0] == bus:
                fields = change_field(flow[1], aggregate)
                flow_label = (
                    bus.label,
                    "out",
                    flow[1].label.cat,
                    fields["tag"],
                    fields["subtag"],
                )

            else:
                fields = change_field(flow[0], aggregate)
                flow_label = (
                    bus.label,
                    "in",
                    flow[0].label.cat,
                    fields["tag"],
                    fields["subtag"],
                )

            if flow_label in data:
                data[flow_label] += results["Main"][flow]["sequences"]["flow"]
            else:
                data[flow_label] = results["Main"][flow]["sequences"]["flow"]

    return data.sort_index(axis=1)
