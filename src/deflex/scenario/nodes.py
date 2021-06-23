# -*- coding: utf-8 -*-

"""Creating solph nodes from input data.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import logging
import warnings
from collections import namedtuple

import pandas as pd
from oemof import solph


class Label(namedtuple("solph_label", ["cat", "tag", "subtag", "region"])):
    """A label for deflex components."""

    __slots__ = ()

    def __str__(self):
        return "_".join(map(str, self._asdict().values())).replace(" ", "-")


def create_solph_nodes_from_data(input_data, nodes):
    """
    Creating solph nodes from input data.

    Parameters
    ----------
    input_data
    nodes

    Returns
    -------

    """
    # Commodity sources
    add_commodity_sources(input_data, nodes)

    # Electricity demand
    add_electricity_demand(input_data, nodes)

    # Volatile sources
    add_volatile_sources(input_data, nodes)

    # Power plants
    add_power_plants(input_data, nodes)

    # Decentralised heating systems
    if "decentralised heat" in input_data:
        add_decentralised_heating_systems(input_data, nodes)

    # District heating demand
    if "heat demand series" in input_data:
        add_district_heating_demand(input_data, nodes)

    # Add chp plants and heat plants for gird-bound heat
    if "heat-chp plants" in input_data:
        add_heat_and_chp_plants(input_data, nodes)

    # Electricity storages
    if "electricity storages" in input_data or "storages" in input_data:
        add_storages(input_data, nodes)

    # Mobility
    if "mobility" in input_data and "mobility demand series" in input_data:
        add_mobility(input_data, nodes)

    # Other commodities
    if "other demand series" in input_data:
        add_other_demand(input_data, nodes)

    if "other converters" in input_data:
        add_other_converters(input_data, nodes)

    # Connect electricity buses with transmission
    if "power lines" in input_data:
        add_transmission_lines_between_electricity_nodes(input_data, nodes)

    # Add shortage excess to every bus
    add_shortage_excess(nodes)
    return nodes


# ************ LABELS ********************************

def electricity_bus_label(region):
    return Label("electricity", "all", "all", region)


def commodity_bus_label(fuel, region):
    return Label("commodity", "all", fuel, region)


# ************ BUSES ********************************

def add_electricity_bus(nodes, region):
    """Create an electricity bus for a given region."""
    bus_label = electricity_bus_label(region)
    if bus_label not in nodes:
        nodes[bus_label] = solph.Bus(label=bus_label)


def check_electricity_buses(nodes, table):
    for region in table.index.get_level_values(0).unique():
        if electricity_bus_label(region) not in nodes:
            add_electricity_bus(nodes, region)


# ************ Objects ********************************

def add_source(nodes, label, bus_label, **params):
    annual_limit = params.get("annual limit", float("inf"))
    variable_costs = params.get("variable costs", 0)
    emissions = params.get("emission", solph.sequence(0))
    capacity = params.get("capacity", None)
    fix = params.get("fix", None)

    if annual_limit <= 0:
        pass
    elif annual_limit == float("inf"):
        nodes[label] = solph.Source(
            label=label,
            outputs={
                nodes[bus_label]: solph.Flow(
                    variable_costs=variable_costs,
                    emission=emissions,
                    nominal_value=capacity,
                    fix=fix,
                )
            },
        )
    else:
        nodes[label] = solph.Source(
            label=label,
            outputs={
                nodes[bus_label]: solph.Flow(
                    variable_costs=variable_costs,
                    emission=emissions,
                    nominal_value=annual_limit,
                    summed_max=1,
                )
            },
        )


def add_sink(nodes, table, input_data, label, bus_label, sink_set):
    if len(sink_set) < 3:
        idx = tuple((table,)) + sink_set + tuple(("None",))
    else:
        idx = tuple((table,)) + sink_set

    if idx in input_data.get("demand response", pd.DataFrame()).index:
        logging.debug("Use demand response sink for {}.".format(idx))
        p = input_data["demand response"].loc[idx]
        nodes[label] = solph.custom.SinkDSM(
            label=label,
            inputs={nodes[bus_label]: solph.Flow()},
            capacity_up=p["capacity up"],
            capacity_down=p["capacity down"],
            delay_time=p["delay"],
            shift_interval=p["shift interval"],
            demand=input_data[table][sink_set],
            method=p["method"],
            cost_dsm_down=p["cost down"],
            cost_dsm_up=p["cost up"],
        )
    else:
        logging.debug("Use normal sink for {}.".format(idx))
        nodes[label] = solph.Sink(
            label=label,
            inputs={
                nodes[bus_label]: solph.Flow(
                    fix=input_data[table][sink_set],
                    nominal_value=1,
                )
            },
        )


# ************ TABLES ********************************

def add_commodity_sources(input_data, nodes):
    """

    Parameters
    ----------
    nodes
    input_data

    Returns
    -------

    """
    for idx, params in input_data["commodity sources"].iterrows():
        name = idx[1].replace("_", " ")
        region = idx[0]

        # Create commodity Bus
        bus_label = commodity_bus_label(name, region)
        nodes[commodity_bus_label(name, region)] = solph.Bus(label=bus_label)

        cs_label = Label("source", "commodity", name, region)

        co2_price = float(input_data["general"]["co2 price"])

        params["variable costs"] = (
            params["emission"] * co2_price + params["costs"]
        )

        add_source(nodes, cs_label, bus_label, **params)
    return nodes


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
    vs = table_collection["volatile plants"]

    for region in vs.index.get_level_values(0).unique():
        for vs_type in vs.loc[region].index:
            vs_label = Label("source", "volatile", vs_type, region)
            capacity = vs.loc[(region, vs_type), "capacity"]
            try:
                feedin = table_collection["volatile series"][region, vs_type]
            except KeyError:
                if capacity > 0:
                    msg = "Missing time series for {0} (capacity: {1}) in {2}."
                    raise ValueError(msg.format(vs_type, capacity, region))
                feedin = [0]
            bus_label = electricity_bus_label(region)
            if bus_label not in nodes:
                nodes[bus_label] = solph.Bus(label=bus_label)
            if capacity * sum(feedin) > 0:
                add_source(
                    nodes, vs_label, bus_label, capacity=capacity, fix=feedin
                )


def add_decentralised_heating_systems(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    logging.debug("Add decentralised_heating_systems to nodes dictionary.")
    dts = table_collection["heat demand series"]
    dh = table_collection["decentralised heat"]

    demand_sets = [c for c in dts.columns if "district heating" not in str(c)]

    for demand_set in demand_sets:
        region_name = demand_set[0]
        system_name = demand_set[1]
        fuel = demand_set[1].replace("_", " ")

        src = dh.loc[demand_set, "source"].replace("_", " ")

        if src == "electricity":
            cs_bus_label = electricity_bus_label(region_name)
            if cs_bus_label not in nodes:
                add_electricity_bus(nodes, region_name)
        else:
            cs_bus_label = commodity_bus_label(src, region_name)

        # Create heating bus as Bus
        heat_bus_label = Label("heat", "decentralised", fuel, region_name)
        nodes[heat_bus_label] = solph.Bus(label=heat_bus_label)

        # Create heating system as Transformer
        trsf_label = Label(
            "decentralised heat", system_name, fuel, region_name
        )

        efficiency = float(dh.loc[demand_set, "efficiency"])

        nodes[trsf_label] = solph.Transformer(
            label=trsf_label,
            inputs={nodes[cs_bus_label]: solph.Flow()},
            outputs={nodes[heat_bus_label]: solph.Flow()},
            conversion_factors={nodes[heat_bus_label]: efficiency},
        )

        # Create demand as Sink
        d_heat_demand_label = Label(
            "heat demand", "decentralised", fuel, region_name
        )
        add_sink(
            nodes,
            "heat demand series",
            table_collection,
            d_heat_demand_label,
            heat_bus_label,
            demand_set,
        )


def add_electricity_demand(input_data, nodes):
    """

    Parameters
    ----------
    input_data
    nodes

    Returns
    -------

    """
    logging.debug("Add local electricity demand to nodes dictionary.")

    for idx, series in input_data["electricity demand series"].items():
        region = idx[0]
        demand_name = idx[1]
        if series.sum() > 0:
            bus_label = electricity_bus_label(region)
            if bus_label not in nodes:
                add_electricity_bus(nodes, region)
            elec_demand_label = Label(
                "electricity demand", "electricity", demand_name, region
            )
            add_sink(
                nodes,
                "electricity demand series",
                input_data,
                elec_demand_label,
                bus_label,
                idx,
            )


def add_district_heating_demand(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    logging.debug("Add district heating systems to nodes dictionary.")
    dts = table_collection["heat demand series"]

    demand_sets = [c for c in dts.columns if "district heating" in str(c)]

    for demand_set in demand_sets:
        region = demand_set[0]
        if dts[demand_set].sum() > 0:
            bus_label = Label("heat", "district", "all", region)
            if bus_label not in nodes:
                nodes[bus_label] = solph.Bus(label=bus_label)
            heat_demand_label = Label("heat demand", "district", "all", region)
            add_sink(
                nodes,
                "heat demand series",
                table_collection,
                heat_demand_label,
                bus_label,
                demand_set,
            )


def add_transmission_lines_between_electricity_nodes(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    logging.debug("Add transmission lines to nodes dictionary.")
    power_lines = table_collection["power lines"]
    for idx, values in power_lines.iterrows():
        b1, b2 = idx.split("-")
        lines = [(b1, b2), (b2, b1)]
        for line in lines:
            line_label = Label("line", "electricity", line[0], line[1])
            bus_label_in = electricity_bus_label(line[0])
            bus_label_out = electricity_bus_label(line[1])
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
                    "Line %s has a capacity of %s", line_label, values.capacity
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
                logging.debug("Line %s has no capacity limit", line_label)
                nodes[line_label] = solph.Transformer(
                    label=line_label,
                    inputs={nodes[bus_label_in]: solph.Flow()},
                    outputs={nodes[bus_label_out]: solph.Flow()},
                    conversion_factors={
                        nodes[bus_label_out]: values.efficiency
                    },
                )


def add_power_plants(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    pp = table_collection["power plants"]

    check_electricity_buses(nodes, pp)

    for idx, params in pp.iterrows():
        region = idx[0]

        # Create label for in and out bus:
        fuel_bus = commodity_bus_label(params.fuel, params["source region"])
        bus_elec = electricity_bus_label(region)

        # Create power plants as 1x1 Transformer if capacity > 0
        if params.capacity > 0:
            # if downtime_factor is in the parameters, use it
            if hasattr(params, "downtime_factor"):
                params.capacity *= 1 - params["downtime_factor"]

            # Define output flow with or without summed_max attribute
            if params.get("annual electricity limit", float("inf")) == float(
                "inf"
            ):
                outflow = solph.Flow(nominal_value=params.capacity)
            else:
                smax = params["annual electricity limit"] / params.capacity
                outflow = solph.Flow(
                    nominal_value=params.capacity, summed_max=smax
                )

            # if variable costs are defined add them to the outflow
            if hasattr(params, "variable_costs"):
                vc = params.variable_costs
                outflow.variable_costs = solph.sequence(vc)

            plant_name = idx[1].replace(" - ", "_").replace(".", "")

            trsf_label = Label("power plant", plant_name, params.fuel, region)

            nodes[trsf_label] = solph.Transformer(
                label=trsf_label,
                inputs={nodes[fuel_bus]: solph.Flow()},
                outputs={nodes[bus_elec]: outflow},
                conversion_factors={nodes[bus_elec]: params.efficiency},
            )


def add_heat_and_chp_plants(table_collection, nodes):
    chp_heat_plants = table_collection["heat-chp plants"]

    check_electricity_buses(nodes, chp_heat_plants)

    for idx, params in chp_heat_plants.iterrows():
        region = idx[0]
        name = idx[1]

        # Check and create buses
        bus_elec = electricity_bus_label(region)
        if params.fuel != "electricity":
            bus_fuel = commodity_bus_label(
                params.fuel, params["source region"]
            )
        else:
            bus_fuel = bus_elec

        bus_heat = Label("heat", "district", "all", region)

        if bus_heat not in nodes:
            nodes[bus_heat] = solph.Bus(label=bus_heat)

        # Create chp plants as 1x2 Transformer
        if (
            hasattr(params, "capacity_heat_chp")
            and params["capacity_heat_chp"] > 0
        ):
            chp_label = Label(
                "chp plant", name, params.fuel.replace("_", " "), region
            )

            smax = (params.limit_heat_chp / params.efficiency_heat_chp) / (
                params["capacity_heat_chp"] / params.efficiency_heat_chp
            )

            nodes[chp_label] = solph.Transformer(
                label=chp_label,
                inputs={
                    nodes[bus_fuel]: solph.Flow(
                        nominal_value=(
                            params["capacity_heat_chp"]
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
        if hasattr(params, "capacity_hp") and params.capacity_hp > 0:
            hp_label = Label(
                "heat plant", name, params.fuel.replace("_", " "), region
            )
            smax = params.limit_hp / params.capacity_hp

            nodes[hp_label] = solph.Transformer(
                label=hp_label,
                inputs={nodes[bus_fuel]: solph.Flow()},
                outputs={
                    nodes[bus_heat]: solph.Flow(
                        nominal_value=params.capacity_hp, summed_max=smax
                    )
                },
                conversion_factors={nodes[bus_heat]: params.efficiency_hp},
            )


def add_storages(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    # Begin ##### Remove the following lines in deflex >= 0.5
    if (
        "electricity storages" in table_collection
        and "storages" in table_collection
    ):
        msg = (
            "'electricity storages' tables are deprecated and cannot be "
            "used together with 'storages'.\nUse 'storages' for all kind "
            "of storages. Define 'storage medium' as 'electricity' for "
            "electricity storages."
        )
        raise ValueError(msg)

    if "electricity storages" in table_collection:
        storage_table = table_collection["electricity storages"]
        storage_table["storage medium"] = "electricity"
        msg = (
            "The 'electricity storages' table is deprecated.\nUse "
            "'storages' for all kind of storages.\nDefine 'storage medium' "
            "as 'electricity' for electricity storages.\nIn the future "
            "such a table will cause an error (deflex >=0.5)."
        )
        warnings.warn(msg, FutureWarning)
    elif "storages" in table_collection:
        storage_table = table_collection["storages"]
    else:
        storage_table = pd.DataFrame()
    # End ##### Remove the following lines in deflex >= 0.5

    for idx, params in storage_table.iterrows():
        region = idx[0]
        name = idx[1]
        storage_label = Label(
            "storage", params["storage medium"], name, region
        )
        if params["storage medium"] == "electricity":
            bus_label = electricity_bus_label(region)
        else:
            bus_label = commodity_bus_label(params["storage medium"], region)
        nodes[storage_label] = solph.components.GenericStorage(
            label=storage_label,
            inputs={
                nodes[bus_label]: solph.Flow(
                    nominal_value=params["charge capacity"]
                )
            },
            outputs={
                nodes[bus_label]: solph.Flow(
                    nominal_value=params["discharge capacity"]
                )
            },
            nominal_storage_capacity=params["energy content"],
            loss_rate=params["loss rate"],
            initial_storage_level=None,
            inflow_conversion_factor=params["charge efficiency"],
            outflow_conversion_factor=params["discharge efficiency"],
        )


def add_other_demand(input_data, nodes):
    logging.debug("Add other demand to nodes dictionary.")

    for idx, series in input_data["other demand series"].items():
        region = idx[0]
        medium = idx[1]
        demand_name = idx[2]
        if series.sum() > 0:
            bus_label = commodity_bus_label(medium, region)
            demand_label = Label("other demand", medium, demand_name, region)
            add_sink(
                nodes,
                "other demand series",
                input_data,
                demand_label,
                bus_label,
                idx,
            )


def add_other_converters(input_data, nodes):
    pp = input_data["other converters"]

    for idx, params in pp.iterrows():
        region = idx[0]

        bus = {}
        for f in ["source", "target"]:
            if params[f] == "electricity":
                bus[f] = electricity_bus_label(params["{} region".format(f)])
            else:
                bus[f] = commodity_bus_label(
                    params[f], params["{} region".format(f)]
                )

        # Create converter as 1x1 Transformer if capacity > 0
        if params.capacity > 0:
            # if downtime_factor is in the parameters, use it
            if hasattr(params, "downtime_factor"):
                params.capacity *= 1 - params["downtime_factor"]

            # Define output flow with or without summed_max attribute
            if params.get("annual limit", float("inf")) == float("inf"):
                outflow = solph.Flow(nominal_value=params.capacity)
            else:
                smax = params["annual limit"] / params.capacity
                outflow = solph.Flow(
                    nominal_value=params.capacity, summed_max=smax
                )

            # if variable costs are defined add them to the outflow
            if hasattr(params, "variable_costs"):
                vc = params.variable_costs
                outflow.variable_costs = solph.sequence(vc)

            plant_name = idx[1].replace(" - ", "_").replace(".", "")

            trsf_label = Label(
                "other converter", plant_name, params.source, region
            )

            nodes[trsf_label] = solph.Transformer(
                label=trsf_label,
                inputs={nodes[bus["source"]]: solph.Flow()},
                outputs={nodes[bus["target"]]: outflow},
                conversion_factors={nodes[bus["target"]]: params.efficiency},
            )


def add_mobility(table_collection, nodes):
    """

    Parameters
    ----------
    table_collection
    nodes

    Returns
    -------

    """
    mseries = table_collection["mobility demand series"]
    mtable = table_collection["mobility"]

    for mset in mseries.columns:
        source = mtable.loc[mset, "source"]
        source_region = mtable.loc[mset, "source region"]
        region = mset[0]
        name = mset[1]
        efficiency = mtable.loc[mset, "efficiency"]

        # Define labels
        converter_label = Label("fuel converter", name, source, region)
        demand_label = Label("mobility demand", "mobility", name, region)
        bus_label = Label("mobility", "all", name, region)
        if source != "electricity":
            fuel_bus_label = commodity_bus_label(source, source_region)
        else:
            fuel_bus_label = electricity_bus_label(source_region)

        # Create mobility Bus
        nodes[bus_label] = solph.Bus(label=bus_label)

        # Create fuel converter (Transformer)
        nodes[converter_label] = solph.Transformer(
            label=converter_label,
            inputs={nodes[fuel_bus_label]: solph.Flow()},
            outputs={nodes[bus_label]: solph.Flow()},
            conversion_factors={nodes[bus_label]: efficiency},
        )

        # Create mobility demand Sink
        add_sink(
            nodes,
            "mobility demand series",
            table_collection,
            demand_label,
            bus_label,
            (region, name),
        )
    return nodes


def add_shortage_excess(nodes):
    """

    Parameters
    ----------
    nodes

    Returns
    -------

    """
    bus_keys = [
        key for key, obj in nodes.items() if isinstance(obj, solph.Bus)
    ]
    for key in bus_keys:
        excess_label = Label("excess", key.cat, key.subtag, key.region)
        nodes[excess_label] = solph.Sink(
            label=excess_label, inputs={nodes[key]: solph.Flow()}
        )
        shortage_label = Label("shortage", key.cat, key.subtag, key.region)
        nodes[shortage_label] = solph.Source(
            label=shortage_label,
            outputs={nodes[key]: solph.Flow(variable_costs=900)},
        )
