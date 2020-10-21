# -*- coding: utf-8 -*-

"""Work with the scenario data.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import calendar
import datetime
import logging
# Python libraries
import os
import shutil
import sys
from collections import namedtuple

import dill as pickle
# External libraries
import networkx as nx
import pandas as pd
from matplotlib import pyplot as plt
# oemof libraries
from oemof import solph
from oemof.tools import logger

if sys.getrecursionlimit() < 3000:
    sys.setrecursionlimit(3000)


class NodeDict(dict):
    __slots__ = ()

    def __setitem__(self, key, item):
        if super().get(key) is None:
            super().__setitem__(key, item)
        else:
            msg = (
                "Key '{0}' already exists. ".format(key)
                + "Duplicate keys are not allowed in a node dictionary."
            )
            raise KeyError(msg)


class Scenario:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "unnamed_scenario")
        self.table_collection = kwargs.get("table_collection", {})
        self.year = kwargs.get("year", None)
        self.ignore_errors = kwargs.get("ignore_errors", False)
        self.round_values = kwargs.get("round_values", 0)
        self.model = kwargs.get("model", None)
        self.es = kwargs.get("es", None)
        self.results = None
        self.results_fn = kwargs.get("results_fn", None)
        self.debug = kwargs.get("debug", None)
        self.location = None
        self.map = None
        self.meta = kwargs.get("meta", None)

    def initialise_energy_system(self):
        if self.debug is True:
            number_of_time_steps = 3
        else:
            try:
                if calendar.isleap(self.year):
                    number_of_time_steps = 8784
                else:
                    number_of_time_steps = 8760
            except TypeError:
                msg = (
                    "You cannot create an EnergySystem with self.year={0}, "
                    "of type {1}."
                )
                raise TypeError(msg.format(self.year, type(self.year)))

        date_time_index = pd.date_range(
            "1/1/{0}".format(self.year), periods=number_of_time_steps, freq="H"
        )
        return solph.EnergySystem(timeindex=date_time_index)

    def load_excel(self, filename=None):
        """Load scenario from an excel-file."""
        if filename is not None:
            self.location = filename
        xls = pd.ExcelFile(self.location)
        for sheet in xls.sheet_names:
            self.table_collection[sheet] = xls.parse(
                sheet, index_col=[0], header=[0, 1]
            )
        return self

    def load_csv(self, path=None):
        """Load scenario from a csv-collection."""
        if path is not None:
            self.location = path
        for file in os.listdir(self.location):
            if file[-4:] == ".csv":
                filename = os.path.join(self.location, file)
                self.table_collection[file[:-4]] = pd.read_csv(
                    filename, index_col=[0], header=[0, 1]
                )
        return self

    def to_excel(self, filename):
        """Dump scenario into an excel-file."""
        # create path if it does not exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        writer = pd.ExcelWriter(filename)
        for name, df in sorted(self.table_collection.items()):
            df.to_excel(writer, name)
        writer.save()
        logging.info("Scenario saved as excel file to {0}".format(filename))

    def to_csv(self, path):
        """Dump scenario into a csv-collection."""
        if os.path.isdir(path):
            shutil.rmtree(os.path.join(path))
        os.makedirs(path)

        for name, df in self.table_collection.items():
            name = name.replace(" ", "_") + ".csv"
            filename = os.path.join(path, name)
            df.to_csv(filename)
        logging.info("Scenario saved as csv-collection to {0}".format(path))

    def check_table(self, table_name):
        if self.table_collection[table_name].isnull().values.any():
            c = []
            for column in self.table_collection[table_name].columns:
                if self.table_collection[table_name][column].isnull().any():
                    c.append(column)
            msg = "Nan Values in the {0} table (columns: {1})."
            raise ValueError(msg.format(table_name, c))
        return self

    def create_nodes(self):
        pass

    def initialise_es(self, year=None):
        if year is not None:
            self.year = year
        self.es = self.initialise_energy_system()
        return self

    def add_nodes(self, nodes):
        """

        Parameters
        ----------
        nodes : dict
            Dictionary with a unique key and values of type oemof.network.Node.

        Returns
        -------
        self

        """
        if self.es is None:
            self.initialise_es()
        self.es.add(*nodes.values())
        return self

    def table2es(self):
        if self.es is None:
            self.es = self.initialise_energy_system()
        nodes = self.create_nodes()
        self.es.add(*nodes.values())
        return self

    def create_model(self):
        self.model = solph.Model(self.es)
        return self

    def dump_es(self, filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        f = open(filename, "wb")
        if self.meta is None:
            if self.es.results is not None and "Meta" in self.es.results:
                self.meta = self.es.results["meta"]
        pickle.dump(self.meta, f)
        pickle.dump(self.es.__dict__, f)
        f.close()
        logging.info("Results dumped to {0}.".format(filename))

    def restore_es(self, filename=None):
        if filename is None:
            filename = self.results_fn
        else:
            self.results_fn = filename
        if self.es is None:
            self.es = solph.EnergySystem()
        f = open(filename, "rb")
        self.meta = pickle.load(f)
        self.es.__dict__ = pickle.load(f)
        f.close()
        self.results = self.es.results["main"]
        logging.info("Results restored from {0}.".format(filename))

    def scenario_info(self, solver_name):
        sc_info = {
            "name": self.name,
            "datetime": datetime.datetime.now(),
            "year": self.year,
            "solver": solver_name,
        }
        return sc_info

    def solve(self, with_duals=False, tee=True, logfile=None, solver=None):
        logging.info("Optimising using {0}.".format(solver))

        if with_duals:
            self.model.receive_duals()

        if self.debug:
            filename = os.path.join(
                solph.helpers.extend_basic_path("lp_files"), "reegis.lp"
            )
            logging.info("Store lp-file in {0}.".format(filename))
            self.model.write(
                filename, io_options={"symbolic_solver_labels": True}
            )

        self.model.solve(
            solver=solver, solve_kwargs={"tee": tee, "logfile": logfile}
        )
        self.es.results["main"] = outputlib.processing.results(self.model)
        self.es.results["meta"] = outputlib.processing.meta_results(self.model)
        self.es.results["param"] = outputlib.processing.parameter_as_dict(
            self.es
        )
        self.es.results["meta"]["scenario"] = self.scenario_info(solver)
        self.es.results["meta"]["in_location"] = self.location
        self.es.results["meta"]["file_date"] = datetime.datetime.fromtimestamp(
            os.path.getmtime(self.location)
        )
        self.es.results["meta"]["oemof_version"] = logger.get_version()
        self.results = self.es.results["main"]

    def plot_nodes(self, show=None, filename=None, **kwargs):

        rm_nodes = kwargs.get("remove_nodes_with_substrings")

        g = graph.create_nx_graph(
            self.es, filename=filename, remove_nodes_with_substrings=rm_nodes
        )
        if show is True:
            draw_graph(g, **kwargs)
        return g


class Label(namedtuple("solph_label", ["cat", "tag", "subtag", "region"])):
    __slots__ = ()

    def __str__(self):
        return "_".join(map(str, self._asdict().values()))


class DeflexScenario(Scenario):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.extra_regions = kwargs.get("extra_regions", list())

    def create_nodes(self):
        # Create  a special dictionary that will raise an error if a key is
        # updated. This avoids the
        nodes = NodeDict()

        # Local volatile sources
        add_volatile_sources(self.table_collection, nodes)

        # Decentralised heating systems
        add_decentralised_heating_systems(
            self.table_collection, nodes, self.extra_regions
        )

        # Local electricity demand
        add_electricity_demand(self.table_collection, nodes)

        # Local district heating demand
        add_district_heating_systems(self.table_collection, nodes)

        # Connect electricity buses with transmission
        add_transmission_lines_between_electricity_nodes(
            self.table_collection, nodes
        )

        # Local power plants as Transformer and ExtractionTurbineCHP (chp)
        add_power_and_heat_plants(
            self.table_collection, nodes, self.extra_regions
        )

        # Storages
        if "storages" in self.table_collection:
            add_storages(self.table_collection, nodes)

        # Add shortage excess to every bus
        add_shortage_excess(nodes)
        return nodes


def create_fuel_bus_with_source(nodes, fuel, region, data):
    bus_label = Label("bus", "commodity", fuel.replace(" ", "_"), region)
    if bus_label not in nodes:
        nodes[bus_label] = solph.Bus(label=bus_label)

    cs_label = Label("source", "commodity", fuel.replace(" ", "_"), region)

    if cs_label not in nodes:
        nodes[cs_label] = solph.Source(
            label=cs_label,
            outputs={
                nodes[bus_label]: solph.Flow(
                    variable_costs=data.loc["costs", fuel.replace("_", " ")],
                    emission=data.loc["emission", fuel.replace("_", " ")],
                )
            },
        )


def add_volatile_sources(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    logging.debug("Add volatile sources to nodes dictionary.")
    vs = table_collection["volatile_source"]

    for region in vs.columns.get_level_values(0).unique():
        for vs_type in vs[region].columns:
            vs_label = Label("source", "ee", vs_type, region)
            capacity = vs.loc["capacity", (region, vs_type)]
            try:
                feedin = table_collection["volatile_series"][region, vs_type]
            except KeyError:
                if capacity > 0:
                    msg = "Missing time series for {0} (capacity: {1}) in {2}."
                    raise ValueError(msg.format(vs_type, capacity, region))
                feedin = [0]
            bus_label = Label("bus", "electricity", "all", region)
            if bus_label not in nodes:
                nodes[bus_label] = solph.Bus(label=bus_label)
            if capacity * sum(feedin) > 0:
                nodes[vs_label] = solph.Source(
                    label=vs_label,
                    outputs={
                        nodes[bus_label]: solph.Flow(
                            actual_value=feedin,
                            nominal_value=capacity,
                            fixed=True,
                            emission=0,
                        )
                    },
                )


def add_decentralised_heating_systems(table_collection, nodes, extra_regions):
    logging.debug("Add decentralised_heating_systems to nodes dictionary.")
    cs = table_collection["commodity_source"]["DE"]
    dts = table_collection["demand_series"]
    dh = table_collection["decentralised_heat"]
    demand_regions = list({"DE_demand"}.union(set(extra_regions)))

    for d_region in demand_regions:
        region_name = d_region.replace("_demand", "")

        if region_name not in dh:
            data_name = "DE_demand"
        else:
            data_name = d_region

        fuels = [f for f in dh[data_name].columns if f in dts[d_region]]
        for fuel in fuels:
            src = dh.loc["source", (data_name, fuel)]
            bus_label = Label(
                "bus", "commodity", src.replace(" ", "_"), region_name
            )

            # Check if source bus exists
            if bus_label not in nodes:
                create_fuel_bus_with_source(nodes, src, region_name, cs)

            # Create heating bus as Bus
            heat_bus_label = Label(
                "bus", "heat", fuel.replace(" ", "_"), region_name
            )
            nodes[heat_bus_label] = solph.Bus(label=heat_bus_label)

            # Create heating system as Transformer
            trsf_label = Label(
                "trsf", "heat", fuel.replace(" ", "_"), region_name
            )

            efficiency = float(dh.loc["efficiency", (data_name, fuel)])

            nodes[trsf_label] = solph.Transformer(
                label=trsf_label,
                inputs={nodes[bus_label]: solph.Flow()},
                outputs={nodes[heat_bus_label]: solph.Flow()},
                conversion_factors={nodes[heat_bus_label]: efficiency},
            )

            # Create demand as Sink
            d_heat_demand_label = Label(
                "demand", "heat", fuel.replace(" ", "_"), region_name
            )
            nodes[d_heat_demand_label] = solph.Sink(
                label=d_heat_demand_label,
                inputs={
                    nodes[heat_bus_label]: solph.Flow(
                        actual_value=dts[d_region, fuel],
                        nominal_value=1,
                        fixed=True,
                    )
                },
            )


def add_electricity_demand(table_collection, nodes):
    logging.debug("Add local electricity demand to nodes dictionary.")
    dts = table_collection["demand_series"]
    dts.columns = dts.columns.swaplevel()
    for region in dts["electrical_load"].columns:
        if dts["electrical_load"][region].sum() > 0:
            bus_label = Label("bus", "electricity", "all", region)
            if bus_label not in nodes:
                nodes[bus_label] = solph.Bus(label=bus_label)
            elec_demand_label = Label("demand", "electricity", "all", region)
            nodes[elec_demand_label] = solph.Sink(
                label=elec_demand_label,
                inputs={
                    nodes[bus_label]: solph.Flow(
                        actual_value=dts["electrical_load", region],
                        nominal_value=1,
                        fixed=True,
                    )
                },
            )


def add_district_heating_systems(table_collection, nodes):
    logging.debug("Add district heating systems to nodes dictionary.")
    dts = table_collection["demand_series"]
    for region in dts["district heating"].columns:
        if dts["district heating"][region].sum() > 0:
            bus_label = Label("bus", "heat", "district", region)
            if bus_label not in nodes:
                nodes[bus_label] = solph.Bus(label=bus_label)
            heat_demand_label = Label("demand", "heat", "district", region)
            nodes[heat_demand_label] = solph.Sink(
                label=heat_demand_label,
                inputs={
                    nodes[bus_label]: solph.Flow(
                        actual_value=dts["district heating", region],
                        nominal_value=1,
                        fixed=True,
                    )
                },
            )


def add_transmission_lines_between_electricity_nodes(table_collection, nodes):
    logging.debug("Add transmission lines to nodes dictionary.")
    power_lines = table_collection["transmission"]["electrical"]
    for idx, values in power_lines.iterrows():
        b1, b2 = idx.split("-")
        lines = [(b1, b2), (b2, b1)]
        for line in lines:
            line_label = Label("line", "electricity", line[0], line[1])
            bus_label_in = Label("bus", "electricity", "all", line[0])
            bus_label_out = Label("bus", "electricity", "all", line[1])
            if bus_label_in not in nodes:
                raise ValueError(
                    "Bus {0} missing for power line from {0} to {1}".format(
                        bus_label_in, bus_label_out
                    )
                )
            if bus_label_out not in nodes:
                raise ValueError(
                    "Bus {0} missing for power line from {0} to {1}".format(
                        bus_label_out, bus_label_in
                    )
                )
            if values.capacity != float("inf"):
                logging.debug(
                    "Line {0} has a capacity of {1}".format(
                        line_label, values.capacity
                    )
                )
                nodes[line_label] = solph.Transformer(
                    label=line_label,
                    inputs={nodes[bus_label_in]: solph.Flow()},
                    outputs={
                        nodes[bus_label_out]: solph.Flow(
                            nominal_value=values.capacity
                        )
                    },
                    conversion_factors={
                        nodes[bus_label_out]: values.efficiency
                    },
                )
            else:
                logging.debug(
                    "Line {0} has no capacity limit".format(line_label)
                )
                nodes[line_label] = solph.Transformer(
                    label=line_label,
                    inputs={nodes[bus_label_in]: solph.Flow()},
                    outputs={nodes[bus_label_out]: solph.Flow()},
                    conversion_factors={
                        nodes[bus_label_out]: values.efficiency
                    },
                )


def add_power_and_heat_plants(table_collection, nodes, extra_regions):
    trsf = table_collection["transformer"]
    cs = table_collection["commodity_source"]["DE"]

    for region in trsf.columns.get_level_values(0).unique():
        bus_heat = Label("bus", "heat", "district", region)
        bus_elec = Label("bus", "electricity", "all", region)
        for fuel in trsf[region].columns:
            # Connect to global fuel bus if not defined as extra region
            if region in extra_regions:
                bus_fuel = Label(
                    "bus", "commodity", fuel.replace(" ", "_"), region
                )
                create_fuel_bus_with_source(nodes, fuel, region, cs)
            else:
                bus_fuel = Label(
                    "bus", "commodity", fuel.replace(" ", "_"), "DE"
                )
                if bus_fuel not in nodes:
                    create_fuel_bus_with_source(
                        nodes, fuel.replace(" ", "_"), "DE", cs
                    )
            params = trsf[region, fuel]

            # Create power plants as 1x1 Transformer
            if params.capacity > 0:
                # Define output flow with or without summed_max attribute
                if params.limit_elec_pp == float("inf"):
                    outflow = solph.Flow(nominal_value=params.capacity)
                else:
                    smax = params.limit_elec_pp / params.capacity
                    outflow = solph.Flow(
                        nominal_value=params.capacity, summed_max=smax
                    )

                trsf_label = Label(
                    "trsf", "pp", fuel.replace(" ", "_"), region
                )
                nodes[trsf_label] = solph.Transformer(
                    label=trsf_label,
                    inputs={nodes[bus_fuel]: solph.Flow()},
                    outputs={nodes[bus_elec]: outflow},
                    conversion_factors={nodes[bus_elec]: params.efficiency},
                )

            # Create chp plants as 1x2 Transformer
            if params.capacity_heat_chp > 0:
                trsf_label = Label(
                    "trsf", "chp", fuel.replace(" ", "_"), region
                )

                smax = (params.limit_heat_chp / params.efficiency_heat_chp) / (
                    params.capacity_heat_chp / params.efficiency_heat_chp
                )

                nodes[trsf_label] = solph.Transformer(
                    label=trsf_label,
                    inputs={
                        nodes[bus_fuel]: solph.Flow(
                            nominal_value=(
                                params.capacity_heat_chp
                                / params.efficiency_heat_chp
                            ),
                            summed_max=smax,
                        )
                    },
                    outputs={
                        nodes[bus_elec]: solph.Flow(),
                        nodes[bus_heat]: solph.Flow(),
                    },
                    conversion_factors={
                        nodes[bus_elec]: params.efficiency_elec_chp,
                        nodes[bus_heat]: params.efficiency_heat_chp,
                    },
                )

            # Create heat plants as 1x1 Transformer
            if params.capacity_hp > 0:
                trsf_label = Label(
                    "trsf", "hp", fuel.replace(" ", "_"), region
                )
                smax = params.limit_hp / params.capacity_hp

                nodes[trsf_label] = solph.Transformer(
                    label=trsf_label,
                    inputs={nodes[bus_fuel]: solph.Flow()},
                    outputs={
                        nodes[bus_heat]: solph.Flow(
                            nominal_value=params.capacity_hp, summed_max=smax
                        )
                    },
                    conversion_factors={nodes[bus_heat]: params.efficiency_hp},
                )


def add_storages(table_collection, nodes):
    storages = table_collection["storages"]
    storages.columns = storages.columns.swaplevel()
    for region in storages["phes"].columns:
        storage_label = Label("storage", "electricity", "phes", region)
        bus_label = Label("bus", "electricity", "all", region)
        params = storages["phes"][region]
        nodes[storage_label] = solph.components.GenericStorage(
            label=storage_label,
            inputs={nodes[bus_label]: solph.Flow(nominal_value=params.pump)},
            outputs={
                nodes[bus_label]: solph.Flow(nominal_value=params.turbine)
            },
            nominal_storage_capacity=params.energy,
            loss_rate=0,
            initial_storage_level=None,
            inflow_conversion_factor=params.pump_eff,
            outflow_conversion_factor=params.turbine_eff,
        )


def add_shortage_excess(nodes):
    bus_keys = [key for key in nodes.keys() if "bus" in key.cat]
    for key in bus_keys:
        excess_label = Label("excess", key.tag, key.subtag, key.region)
        nodes[excess_label] = solph.Sink(
            label=excess_label, inputs={nodes[key]: solph.Flow()}
        )
        shortage_label = Label("shortage", key.tag, key.subtag, key.region)
        nodes[shortage_label] = solph.Source(
            label=shortage_label,
            outputs={nodes[key]: solph.Flow(variable_costs=900)},
        )


def draw_graph(
    grph,
    edge_labels=True,
    node_color="#AFAFAF",
    edge_color="#CFCFCF",
    plot=True,
    node_size=2000,
    with_labels=True,
    arrows=True,
    layout="neato",
):
    """
    Draw a graph. This function will be removed in future versions.

    Parameters
    ----------
    grph : networkxGraph
        A graph to draw.
    edge_labels : boolean
        Use nominal values of flow as edge label
    node_color : dict or string
        Hex color code oder matplotlib color for each node. If string, all
        colors are the same.

    edge_color : string
        Hex color code oder matplotlib color for edge color.

    plot : boolean
        Show matplotlib plot.

    node_size : integer
        Size of nodes.

    with_labels : boolean
        Draw node labels.

    arrows : boolean
        Draw arrows on directed edges. Works only if an optimization_model has
        been passed.
    layout : string
        networkx graph layout, one of: neato, dot, twopi, circo, fdp, sfdp.
    """
    if type(node_color) is dict:
        node_color = [node_color.get(g, "#AFAFAF") for g in grph.nodes()]

    # set drawing options
    options = {
        "prog": "dot",
        "with_labels": with_labels,
        "node_color": node_color,
        "edge_color": edge_color,
        "node_size": node_size,
        "arrows": arrows,
    }

    # draw graph
    pos = nx.drawing.nx_agraph.graphviz_layout(grph, prog=layout)

    nx.draw(grph, pos=pos, **options)

    # add edge labels for all edges
    if edge_labels is True and plt:
        labels = nx.get_edge_attributes(grph, "weight")
        nx.draw_networkx_edge_labels(grph, pos=pos, edge_labels=labels)

    # show output
    if plot is True:
        plt.show()


if __name__ == "__main__":
    pass
