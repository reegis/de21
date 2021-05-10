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


def storage_results2table(results):
    storages = set(
        [
            k[0]
            for k in results["main"].keys()
            if isinstance(k[0], solph.GenericStorage)
        ]
    )

    levels = [[], [], [], [], []]
    store = pd.DataFrame(columns=pd.MultiIndex(levels=levels, codes=levels))
    for storage in storages:
        for col in results["main"][storage, None]["sequences"].columns:
            store[
                storage.label.cat,
                storage.label.tag,
                storage.label.subtag,
                storage.label.region,
                col,
            ] = results["main"][storage, None]["sequences"][col]
    return store


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
    >>> from deflex.postprocessing import restore_results, dict2file
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
    tables["storages"] = storage_results2table(results)
    tables["pyomo"] = pyomo_results2series(results)
    tables["meta"] = meta_results2series(results)
    return tables


class Edge:
    def __init__(self, **kwargs):
        self.nodes = kwargs.get("nodes", None)
        self.sequence = kwargs.get("sequence", None)
        self.weight = kwargs.get("weight", None)
        self.color = kwargs.get("color", None)


class DeflexGraph:
    def __init__(self, results, **kwargs):
        """

        Parameters
        ----------
        results : dict
            Deflex results dictionary.

        Other Parameters
        ----------------
        default_node_color : str
            The default color as a dictionary with the keys "fg" for the
            foreground color (font color) and "bg" for the background color
            (fill color). The color has to be a hexadecimal string. The default
            color is used if no other color is set.
            (default: {"bg": "#6a6a72", "fg": "#000000"}")
        default_edge_color : str
            The default edge color as a hexadecimal string. The default color
            is used if no other color is set.
            (default: "#000000"")

        Examples
        --------
        >>> import os
        >>> from deflex.tools import fetch_test_files
        >>> from deflex.postprocessing import restore_results
        >>> from deflex.postprocessing import DeflexGraph
        >>> fn = fetch_test_files("de03_fictive.dflx")
        >>> my_results = restore_results(fn)
        >>> dflx_graph = DeflexGraph(my_results)
        >>> sorted(k.__name__ for k in dflx_graph.group_nodes_by_type())
        ['Bus', 'GenericStorage', 'Sink', 'Source', 'Transformer']

        >>> nx_graph = dflx_graph.get()
        >>> nx.number_of_nodes(nx_graph)
        236
        >>> nx.number_weakly_connected_components(nx_graph)
        1
        >>> fn_out = fn.replace(".dflx", "_graph.graphml")
        >>> dflx_graph.write(fn_out)
        >>> os.path.isfile(fn_out)
        True
        >>> os.remove(fn_out)
        """
        self.results = results
        self.default_node_color = kwargs.get(
            "default_node_color", {"bg": "#6a6a72", "fg": "#000000"}
        )
        self.default_edge_color = kwargs.get("default_edge_color", "#000000")
        self.nodes = self._fetch_nodes()
        self.edges = self._fetch_edges()
        self.graph = None

    def _fetch_edges(self):
        """
        Fetch all edges from the results dictionary and create Edge objects.
        """
        edges = []
        for n in self.results["main"]:
            if n[1] is not None:
                seq = self.results["main"][n]["sequences"]["flow"]
                edges.append(
                    Edge(
                        nodes=n,
                        weight=seq.sum(),
                        color=self.default_edge_color,
                        sequence=seq,
                    )
                )
        return edges

    def _fetch_nodes(self):
        """Fetch all nodes from the results dictionary."""
        nodes = [n[0] for n in self.results["main"].keys()]
        nodes.extend(
            [n[1] for n in self.results["main"].keys() if n[1] is not None]
        )
        return list(set(nodes))

    def group_nodes_by_type(self, use_name=False):
        """
        Group all nodes by types returning a dictionary with the types or the
        name of the types as keys and the list of nodes as value.

        Parameters
        ----------
        use_name : bool
            Use the name of the class instead of the class as key.

        Returns
        -------
        All nodes sorted by their type. The keys of the dictionary are the
        classes (or name of the classes) the values are lists with nodes of
        the corresponding class.

        Examples
        --------
        >>> from deflex.tools import fetch_test_files
        >>> from deflex.postprocessing import restore_results
        >>> from deflex.postprocessing import DeflexGraph
        >>> fn = fetch_test_files("de03_fictive.dflx")
        >>> my_results = restore_results(fn)
        >>> dflx_graph = DeflexGraph(my_results)
        >>> sorted(dflx_graph.group_nodes_by_type(use_name=True))
        ['Bus', 'GenericStorage', 'Sink', 'Source', 'Transformer']
        >>> list(dflx_graph.group_nodes_by_type(use_name=False))[0].__mro__[-2]
        <class 'oemof.network.network.Node'>
        """
        node_groups = {}
        node_types = set([type(n) for n in sorted(self.nodes)])
        for node_type in node_types:
            if use_name is True:
                name = node_type.__name__
            else:
                name = node_type
            node_groups[name] = [
                n for n in self.nodes if isinstance(n, node_type)
            ]
        return node_groups

    def color_nodes_by_type(self, colors, use_name=True):
        """
        Color all nodes in a specific color according to the class. Use the
        :py:meth:`group_nodes_by_type` method to get all existing types. Now
        a color can be assigned to every type using a color dictionary. If no
        color is defined for an existing class the default color is used. By
        default the name of each class is used.

        Parameters
        ----------
          colors : dict
            The dictionary needs to have the class (name of class) as keys and
            a color dictionary as value. The color dictionary has two keys,
            "fg" for the foreground color (font color) and "bg" for the
            background color (fill color) and the color as value. The color has
            to be in the hexadecimal style.
        use_name : bool
            Use the name of the class instead of the class as key. If the class
            is used, the classes also have to be used for the colors as key.

        Examples
        --------
        >>> from deflex.tools import fetch_test_files
        >>> from deflex.postprocessing import restore_results
        >>> from deflex.postprocessing import DeflexGraph
        >>> from oemof import solph
        >>> fn = fetch_test_files("de03_fictive.dflx")
        >>> my_results = restore_results(fn)
        >>> dflx_graph = DeflexGraph(my_results)
        >>> my_colors = {
        ...     "Bus": {"bg": "#00ff11", "fg": "#000000"},
        ...     "GenericStorage": {"bg": "#efb507", "fg": "#000000"},
        ...     "Transformer": {"bg": "#94221d", "fg": "#000000"},
        ...     "Source": {"bg": "#996967", "fg": "#000000"},
        ...     "Sink": {"bg": "#31306e", "fg": "#ffffff"},
        ... }
        >>> dflx_graph.color_nodes_by_type(my_colors)
        >>> bus = [n for n in dflx_graph.nodes if isinstance(n, solph.Bus)][0]
        >>> getattr(bus, "bgcolor")
        '#00ff11'
        >>> sorted(set([n.bgcolor for n in dflx_graph.nodes]))
        ['#00ff11', '#31306e', '#94221d', '#996967', '#efb507']
        >>> sorted(set([n.fgcolor for n in dflx_graph.nodes]))
        ['#000000', '#ffffff']
        >>> my_colors = {
        ...     solph.Bus: {"bg": "#00ff11", "fg": "#000000"},
        ...     "GenericStorage": {"bg": "#efb507", "fg": "#000000"},
        ...     "Transformer": {"bg": "#94221d", "fg": "#000000"},
        ...     solph.Source: {"bg": "#996967", "fg": "#000000"},
        ...     solph.Sink: {"bg": "#31306e", "fg": "#ffffff"},
        ... }
        >>> dflx_graph.color_nodes_by_type(my_colors, use_name=False)
        >>> bus = [n for n in dflx_graph.nodes if isinstance(n, solph.Bus)][0]
        >>> getattr(bus, "bgcolor")
        '#00ff11'
        >>> sorted(set([n.bgcolor for n in dflx_graph.nodes]))
        ['#00ff11', '#31306e', '#6a6a72', '#996967']
        >>> sorted(set([n.fgcolor for n in dflx_graph.nodes]))
        ['#000000', '#ffffff']
        """
        groups = self.group_nodes_by_type(use_name)
        for ntype, nodes in groups.items():
            type_color = colors.get(ntype, self.default_node_color)
            for n in nodes:
                n.bgcolor = type_color["bg"]
                n.fgcolor = type_color["fg"]
        self.graph = None

    def color_nodes_by_substring(self, colors):
        """
        Color all nodes in a specific color according to a given substring. A
        color can be assigned to every substring using a dictionary with the
        substrings as key an the color dictionary as value. The color
        dictionary needs to have the keys "fg" for the foreground color (font
        color) and "bg" for the background color (fill color). The color has to
        be in the hexadecimal style. Each substring key will be compared with
        the label of the node as string. If no substring match
        the default node color is used. If more than one substring is within
        a label the last match will overwrite the previous matches.

        Parameters
        ----------
        colors : dict
            The dictionary needs to have the substring as keys and a color
            dictionary as value. The color dictionary has two keys, "fg" for
            the foreground color (font color) and "bg" for the background color
            (fill color) and the color as value. The color has to be in the
            hexadecimal style.

        Examples
        --------
        >>> from deflex.tools import fetch_test_files
        >>> from deflex.postprocessing import restore_results
        >>> from deflex.postprocessing import DeflexGraph
        >>> fn = fetch_test_files("de03_fictive.dflx")
        >>> my_results = restore_results(fn)
        >>> dflx_graph = DeflexGraph(my_results)
        >>> my_colors = {
        ...     "H2": {"bg": "#00ff11", "fg": "#000000"},
        ...     "electricity": {"bg": "#efb507", "fg": "#000000"},
        ...     "bioenergy": {"bg": "#063313", "fg": "#ffffff"},
        ... }
        >>> dflx_graph.color_nodes_by_substring(my_colors)
        >>> node = [n for n in dflx_graph.nodes if "bioenergy" in n.label][0]
        >>> getattr(node, "bgcolor")
        '#063313'
        >>> sorted(set([n.bgcolor for n in dflx_graph.nodes]))
        ['#00ff11', '#063313', '#6a6a72', '#efb507']
        >>> sorted(set([n.fgcolor for n in dflx_graph.nodes]))
        ['#000000', '#ffffff']
        """
        for node in self.nodes:
            node.bgcolor = self.default_node_color["bg"]
            node.fgcolor = self.default_node_color["fg"]
        for substring, color in colors.items():
            nodes = [n for n in self.nodes if substring in str(n.label)]
            for node in nodes:
                node.bgcolor = color["bg"]
                node.fgcolor = color["fg"]

    def color_edges_by_weight(self, cmap="cool", max_weight=None):
        """
        Color all edges by their weight using a matplotlib color map (cmap). If
        no maximum weight is give the highest weight is used.

        Parameters
        ----------
        cmap : str
            Name of the matplotlib color map.
        max_weight : numeric
            The maximum for the normalisation of the weights. All number above
            the max_weight will get the color of the maximum. If no value is
            given the maximum weight of all edges will used.

        Examples
        --------
        >>> from deflex.tools import fetch_test_files
        >>> from deflex.postprocessing import restore_results
        >>> from deflex.postprocessing import DeflexGraph
        >>> from matplotlib.cm import get_cmap
        >>>
        >>> fn = fetch_test_files("de03_fictive.dflx")
        >>> my_results = restore_results(fn)
        >>> dflx_graph = DeflexGraph(my_results)
        >>> round(dflx_graph.max_edge_weight()/10**6, 2)
        8.68
        >>> dflx_graph.color_edges_by_weight(cmap="rainbow", max_weight=80)
        >>> edges = dflx_graph.edges
        >>> bus = [e for e in edges if "shortage" in e.nodes[0].label][0]
        >>> getattr(bus, "color")
        '#8000ff'
        >>> w = bus.weight
        >>> rgb2hex(get_cmap("rainbow")(w))
        '#8000ff'
        >>> w
        0.0
        """
        cmap = get_cmap(cmap)
        if max_weight is None:
            max_weight = self.max_edge_weight()
        norm = Normalize(vmin=0.0, vmax=max_weight)
        for e in self.edges:
            e.color = rgb2hex(cmap(norm(e.weight)))
        self.graph = None

    def max_edge_weight(self):
        return pd.Series([e.weight for e in self.edges]).max()

    def create_di_graph(self, weight_exponent=0):
        self.graph = nx.DiGraph()
        for n in self.nodes:
            self.graph.add_node(
                str(n.label),
                label=str(n.label),
                bg_color=getattr(n, "bgcolor", self.default_node_color["bg"]),
                fg_color=getattr(n, "fgcolor", self.default_node_color["fg"]),
                type=n.__class__.__name__,
            )

        for e in self.edges:
            self.graph.add_edge(
                str(e.nodes[0].label),
                str(e.nodes[1].label),
                weigth=format(e.weight * 10 ** weight_exponent, ".1f"),
                color=getattr(e, "color", self.default_edge_color),
                sequence=str(e.sequence.values),
            )
        return self

    def write(self, filename, **kwargs):
        nx.write_graphml(self.get(**kwargs), filename)

    def get(self, **kwargs):
        if self.graph is None:
            self.create_di_graph(
                weight_exponent=kwargs.get("weight_exponent", 0)
            )
        return self.graph
