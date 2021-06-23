# -*- coding: utf-8 -*-

"""Work with the scenario data.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import calendar
import datetime
import logging
import os
import shutil
import sys
import warnings

import dill as pickle
import pandas as pd
from oemof import solph
from oemof.network import graph

from deflex import config as cfg
from .nodes import create_solph_nodes_from_data

if sys.getrecursionlimit() < 3000:
    sys.setrecursionlimit(3000)


class NodeDict(dict):
    """
    A dictionary where existing key-value-pairs cannot be overwritten.

    A NodeDict can collect values with unique keys. Therefore a duplicate key
    will raise a ``KeyError`` instead of overwriting the existing key
    silently.
    """

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
    """
    Basic scenario class.

    Attributes
    ----------
    input_data : dict
        The input data is organised in a dictionary of pandas.DataFrame/
        pandas.Series. The keys are the data names (string) and the values are
        the data tables.
    results : dict
        The results are stored in a dictionary with tuples as keys and the
        results as values (nested dictionary with pandas.DataFrame). The tuples
        contain the node object in the following form:
        (from_node, to_node) for flows and (node, None) for components. See the
        `solph documentation
        <https://oemof-solph.readthedocs.io/en/latest/usage.html#handling-results>`_
        for more details.
    meta : dict
        Meta information that can be used to search for in stored scenarios.
        The dictionary keys can be used like tags or categories.
    es : oemof.solph.EnergySystem
        This attribute will hold the oemof.solph.EnergySystem.

    """

    def __init__(self, **kwargs):
        self.meta = kwargs.get("meta", {})
        self.input_data = kwargs.get("input_data", {})
        self.es = kwargs.get("es", None)
        self.results = kwargs.get("results", None)

    def initialise_energy_system(self):
        """
        Create a solph.EnergySystem and store it in the es attribute. The
        input_data attribute has to contain the input data to use this method.

        Returns
        -------
        self

        """
        if not self.input_data:
            raise ValueError(
                "There is no input data in the scenario. You cannot "
                "initialise an energy system without a year and the number of "
                "time steps."
            )
        year = int(self.input_data["general"]["year"])
        time_steps = int(self.input_data["general"]["number of time steps"])
        # increment = self.input_data["general"]["time increment"]

        # Check leap year
        if calendar.isleap(year) and time_steps != 8784:
            msg = "{0} is a leap year but the number of time steps is {1}."
            warnings.warn(msg.format(year, time_steps), UserWarning)

        # Check series tables
        for key in [t for t in self.input_data.keys() if "series" in t]:
            if time_steps != len(self.input_data[key]):
                msg = (
                    "Number of time steps is {0} but the length of the {1}"
                    " table is {2}."
                ).format(time_steps, key, len(self.input_data[key]))
                raise ValueError(msg)

        # Create datetime index
        date_time_index = pd.date_range(
            "1/1/{0}".format(year), periods=time_steps, freq="H"
        )

        self.es = solph.EnergySystem(timeindex=date_time_index)

        return self

    def read_xlsx(self, filename):
        """Load scenario from an xlsx file. The full path has to be passed."""
        xlsx = pd.ExcelFile(filename)
        for sheet in xlsx.sheet_names:
            table_index_header = cfg.get_list("table_index_header", sheet)
            self.input_data[sheet] = xlsx.parse(
                sheet,
                index_col=list(range(int(table_index_header[0]))),
                header=list(range(int(table_index_header[1]))),
                squeeze=("series" not in sheet),
            )
        self.check_input_data(warning=False)
        self.add_meta_data()
        return self

    def read_csv(self, path):
        """
        Load scenario from a csv-collection. The path of the directory has
        to be passed.
        """
        for file in os.listdir(path):
            if file[-4:] == ".csv":
                name = file[:-4]
                table_index_header = cfg.get_list("table_index_header", name)
                filename = os.path.join(path, file)
                self.input_data[name] = pd.read_csv(
                    filename,
                    index_col=list(range(int(table_index_header[0]))),
                    header=list(range(int(table_index_header[1]))),
                    squeeze=("series" not in name),
                )
        self.check_input_data(warning=False)
        self.add_meta_data()
        return self

    def add_meta_data(self):
        if "info" in self.input_data:
            self.meta.update(self.input_data["info"].to_dict())
        self.meta.update(self.input_data["general"].to_dict())

    def check_input_data(self, warning=False):
        """
        Check the input data for NaN values. If warning is True a warning
        for all tables is raised that contain NaN values. Otherwise an
        exception is raised on the first occurrence of NaN values.
        """
        for sheet, table in self.input_data.items():
            msg = (
                "NaN values found in table:'{0}', column(s): {1}.\n"
                "Empty cells are not allowed in a scenario to avoid "
                "unwanted behaviour.\nRemove the whole column/row if "
                "a parameter is not needed (optional). Consider that 0, 'inf' "
                "or 1 might be neutral values to replace NaN values."
            )
            if isinstance(table, pd.DataFrame):
                table.dropna(thresh=1, inplace=True, axis=0)
                table.dropna(thresh=1, inplace=True, axis=1)
                if table.isnull().any().any():
                    columns = tuple(table.loc[:, table.isnull().any()].columns)
                    msg = msg.format(sheet, columns)
                    if warning is True:
                        warnings.warn(msg, UserWarning)
                    else:
                        raise ValueError(msg)
                self.input_data[sheet] = table.dropna(
                    thresh=(len(table.columns))
                )
            else:
                if table.isnull().any():
                    value = table.loc[table.isnull()].index
                    msg = msg.format(sheet, value)
                    if warning is True:
                        warnings.warn(msg, UserWarning)
                    else:
                        raise ValueError(msg)

        if isinstance(self.input_data["volatile plants"], pd.Series):
            self.input_data["volatile plants"] = pd.DataFrame(
                self.input_data["volatile plants"],
                columns=[self.input_data["volatile plants"].name],
            )

    def to_xlsx(self, filename):
        """Dump the input data as an xlsx-file."""
        # create path if it does not exist
        suffix = filename.split(".")[-1]
        if not suffix == "xlsx":
            filename = filename + ".xlsx"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        writer = pd.ExcelWriter(filename)
        for name, df in sorted(self.input_data.items()):
            df.to_excel(writer, name)
        writer.save()
        logging.info("Scenario saved as excel file to %s", filename)

    def to_csv(self, path):
        """Dump input data as a csv-collection."""
        if os.path.isdir(path):
            shutil.rmtree(os.path.join(path))
        os.makedirs(path)

        for name, df in self.input_data.items():
            name += ".csv"
            filename = os.path.join(path, name)
            df.to_csv(filename)
        logging.info("Scenario saved as csv-collection to %s", path)

    def create_nodes(self):
        """This method is a placeholder for the child classes."""

    def compute(self, solver="cbc", **kwargs):
        """
        Create a solph.Model from the input data and optimise it using an
        external solver. Afterwards the results are stored in the results
        attribute.

        Parameters
        ----------
        solver : str
            The name of the solver as used in the Pyomo package (cbc, glpk,
            gurobi, cplex...).


        """
        self.table2es()
        model = self.create_model()
        self.solve(model, solver=solver, **kwargs)

    def add_nodes_to_es(self, nodes):
        """
        Add nodes to an existing solph.EnergySystem. If the EnergySystem does
        not exist an Error is raised. This method is included in the
        :py:meth:`~deflex.scenario.Scenario.compute()` method and is only
        needed for advanced usage.

        Parameters
        ----------
        nodes : dict
            Dictionary with a unique key and values of type oemof.network.Node.

        Returns
        -------
        self

        """
        self.es.add(*nodes.values())
        return self

    def table2es(self):
        """
        Create a populated solph.EnergySystem from the input data. This method
        is included in the :py:meth:`~deflex.scenario.Scenario.compute()`
        method and is only needed for advanced usage.

        Returns
        -------
        self

        """
        if self.es is None:
            logging.info("Initialise a solph energy system.")
            self.initialise_energy_system()
        logging.info("Creating nodes...")
        self.es.add(*self.create_nodes().values())
        logging.info("Done. Nodes added to the energy system.")
        return self

    def create_model(self):
        """
        This method is included in the
        :py:meth:`~deflex.scenario.Scenario.compute()` method and is only
        needed for advanced usage.

        Returns
        -------
        solph.Model

        """
        logging.info("Creating the model this may take a while...")
        model = solph.Model(self.es)
        logging.info("...Done.")
        return model

    def compute_debug(self):
        """
        The plan is to make it easy to debug an energy system.

        1. Create an EnergySystem with just 5 time steps
        2. Reduce the input data (all series) to 5 time steps
        3. Plot the graph (try/except)
        4. Write an LP file (try/except)
        5. Solve and dump the results (try/except)

        model = solph.Model(self.es)

        filename = os.path.join(solph.helpers.extend_basic_path("lp_files"),
        "reegis.lp")

        logging.info("Store lp-file in %s.", filename)

        model.write(filename, io_options={"symbolic_solver_labels": True})

        """

    def dump(self, filename):
        """
        Store the scenario class into the binary pickle format with the suffix
        `.dflx`. If the given filename does not contain the suffix, it will be
        added to the filename.
        """
        suffix = filename.split(".")[-1]
        if not suffix == "dflx":
            filename = filename + ".dflx"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        f = open(filename, "wb")
        pickle.dump(self.meta, f)
        pickle.dump(self.__dict__, f)
        f.close()
        logging.info("Results dumped to %s.", filename)

    def solve(self, model, solver="cbc", with_duals=False, **solver_kwargs):
        """
        Solve the solph.Model. This method is included in the
        :py:meth:`~deflex.scenario.Scenario.compute()` method and is only
        needed for advanced usage.

        Parameters
        ----------
        model : oemof.solph.Model
        solver : str
        with_duals : bool

        Other Parameters
        ----------------
        tee : bool
            Set to `False` to suppress the solver output (default: True).
        logfile : str
            Define the path where to store the log file of the solver.

        """
        logging.info("Optimising using %s.", solver)

        solver_kwargs["tee"] = solver_kwargs.get("tee", True)

        self.meta["solph_version"] = solph.__version__
        self.meta["solver"] = solver
        self.meta["solver_start"] = datetime.datetime.now()

        if with_duals:
            model.receive_duals()

        model.solve(solver=solver, solve_kwargs=solver_kwargs)

        self.meta["solver_end"] = datetime.datetime.now()

        self.es.results["main"] = solph.processing.results(model)
        self.meta.update(solph.processing.meta_results(model))
        self.es.results["param"] = solph.processing.parameter_as_dict(self.es)
        self.es.results["meta"] = self.meta

        self.results = self.es.results

    def plot_nodes(self, filename=None, **kwargs):
        """
        Plot a graph plot of the energy system and store it into a `.graphml`
        file. The kwargs are passed to the oemof.network function
        `create_nx_graph()
        <https://github.com/oemof/oemof.network/blob/dev/src/oemof/network/graph.py#L15>`_.

        Parameters
        ----------
        filename
        kwargs

        Returns
        -------

        """

        g = graph.create_nx_graph(self.es, filename=filename, **kwargs)

        return g


class DeflexScenario(Scenario):
    """
    The Deflex Scenario inherits from the Scenario class and extends the
    Scenario class with valid nodes creation. Additionally one can define
    an extra_regions attribute to create an extra commodity source for these
    regions. This makes it possible to create a source balance for these
    regions.

    Attributes
    ----------
    extra_regions : list
        All regions with separate commodity sources. This will blow up the
        model a bit but makes it easier to create separate source balances.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_nodes(self):
        """
        Creates solph components and buses from the input data and store them
        in a dictionary with unique IDs as keys.

        Returns
        -------
        dict

        """
        # Create  a special dictionary that will raise an error if a key is
        # updated. This avoids the
        nodes = NodeDict()

        return create_solph_nodes_from_data(self.input_data, nodes)



