# -*- coding: utf-8 -*-

"""
Test the main module

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import os
import shutil
from unittest.mock import MagicMock

import pandas as pd
from reegis import config
from scenario_builder import demand, feedin, powerplants

from deflex import __file__ as dfile
from deflex import config as cfg
from deflex import scenario as st
from deflex.creator import scenario_creator
from deflex.geometries import deflex_power_lines, deflex_regions
from deflex.tools import TEST_PATH


class TestScenarioCreationFull:
    @classmethod
    def setup_class(cls):
        path = os.path.join(TEST_PATH, "de22_heat_transmission_csv")
        sc = st.DeflexScenario()
        sc.read_csv(path)
        cls.tables = sc.input_data
        tmp_tables = {}
        parameter = {
            "costs_source": "ewi",
            "downtime_bioenergy": 0.1,
            "limited_transformer": "bioenergy",
            "local_fuels": "district heating",
            "map": "de22",
            "mobility_other": "petrol",
            "round": 1,
            "separate_heat_regions": "de22",
            "copperplate": False,
            "default_transmission_efficiency": 0.9,
            "group_transformer": False,
            "heat": True,
            "use_CO2_costs": True,
            "use_downtime_factor": True,
            "use_variable_costs": False,
            "year": 2014,
        }
        config.init(paths=[os.path.dirname(dfile)])
        for option, value in parameter.items():
            cfg.tmp_set("creator", option, str(value))
            config.tmp_set("creator", option, str(value))

        name = "heat_demand_deflex"
        fn = os.path.join(os.path.dirname(__file__), "data", name + ".csv")
        tmp_tables[name] = pd.read_csv(fn, index_col=[0], header=[0, 1])

        name = "transformer_balance"
        fn = os.path.join(os.path.dirname(__file__), "data", name + ".csv")
        tmp_tables[name] = pd.read_csv(fn, index_col=[0, 1, 2], header=[0])

        powerplants.scenario_powerplants = MagicMock(
            return_value={
                "volatile plants": cls.tables["volatile plants"],
                "power plants": cls.tables["power plants"],
            }
        )

        powerplants.scenario_chp = MagicMock(
            return_value={
                "heat-chp plants": cls.tables["heat-chp plants"],
                "power plants": cls.tables["power plants"],
            }
        )

        feedin.scenario_feedin = MagicMock(
            return_value=cls.tables["volatile series"]
        )

        demand_table = {
            "electricity demand series": cls.tables[
                "electricity demand series"
            ],
            "heat demand series": cls.tables["heat demand series"],
        }
        demand.scenario_demand = MagicMock(return_value=demand_table)

        name = "deflex_2014_de22_heat_transmission"

        polygons = deflex_regions(rmap=parameter["map"], rtype="polygons")
        lines = deflex_power_lines(parameter["map"]).index
        cls.input_data = scenario_creator.create_scenario(
            polygons, 2014, name, lines
        )

    @classmethod
    def teardown_class(cls):
        pass

    def test_volatile_source(self):
        pd.testing.assert_frame_equal(
            self.tables["volatile plants"],
            self.input_data["volatile plants"],
        )

    def test_storages(self):
        a = self.tables["electricity storages"].apply(pd.to_numeric)
        b = self.input_data["electricity storages"].apply(pd.to_numeric)
        b["energy inflow"] *= 48 / 8760
        for col in a.columns:
            pd.testing.assert_series_equal(a[col], b[col])
        # pd.testing.assert_frame_equal(a, b)

    def test_electricity_demand_series(self):
        pd.testing.assert_frame_equal(
            self.tables["electricity demand series"],
            self.input_data["electricity demand series"],
        )

    def test_heat_demand_series(self):
        pd.testing.assert_frame_equal(
            self.tables["heat demand series"],
            self.input_data["heat demand series"],
        )

    def test_transmission(self):
        self.input_data["power lines"].drop("distance", axis=1, inplace=True)
        self.tables["power lines"].index.name = "name"
        pd.testing.assert_frame_equal(
            self.tables["power lines"].apply(pd.to_numeric).astype(float),
            self.input_data["power lines"].apply(pd.to_numeric),
            rtol=1e-3,
        )

    def test_transformer(self):
        pd.testing.assert_frame_equal(
            self.tables["power plants"],
            self.input_data["power plants"],
        )

    def test_general(self):
        pd.testing.assert_series_equal(
            self.tables["general"].astype(str).sort_index(),
            self.input_data["general"]["value"].astype(str).sort_index(),
        )

    def test_commodity_source(self):
        pd.testing.assert_frame_equal(
            self.tables["commodity sources"],
            self.input_data["commodity sources"]
            .apply(pd.to_numeric)
            .astype(float),
        )

    def test_mobility_series(self):
        pd.testing.assert_frame_equal(
            self.tables["mobility demand series"],
            self.input_data["mobility demand series"].iloc[0:48],
        )

    def test_mobility(self):
        self.input_data["mobility"]["efficiency"] = pd.to_numeric(
            self.input_data["mobility"]["efficiency"]
        )
        pd.testing.assert_frame_equal(
            self.tables["mobility"],
            self.input_data["mobility"],
        )

    def test_chp_hp(self):
        pd.testing.assert_frame_equal(
            self.tables["heat-chp plants"],
            self.input_data["heat-chp plants"],
        )

    def test_decentralised_heat(self):
        pd.testing.assert_frame_equal(
            self.tables["decentralised heat"],
            self.input_data["decentralised heat"],
        )

    def test_volatile_series(self):
        pd.testing.assert_frame_equal(
            self.tables["volatile series"],
            self.input_data["volatile series"],
        )

    def test_length(self):
        assert len(self.tables.keys()) == len(self.input_data.keys())
        assert sorted(list(self.tables.keys())) == sorted(
            list(self.input_data.keys())
        )


class TestScenarioCreationPart:
    @classmethod
    def setup_class(cls):
        path = os.path.join(TEST_PATH, "de21_no-heat_csv")
        sc = st.DeflexScenario()
        sc.read_csv(path)
        cls.tables = sc.input_data
        tmp_tables = {}

        name = "heat_demand_deflex"
        fn = os.path.join(os.path.dirname(__file__), "data", name + ".csv")
        tmp_tables[name] = pd.read_csv(fn, index_col=[0], header=[0, 1])

        name = "transformer_balance"
        fn = os.path.join(os.path.dirname(__file__), "data", name + ".csv")
        tmp_tables[name] = pd.read_csv(fn, index_col=[0, 1, 2], header=[0])

        powerplants.scenario_powerplants = MagicMock(
            return_value={
                "volatile plants": cls.tables["volatile plants"],
                "power plants": cls.tables["power plants"],
            }
        )

        feedin.scenario_feedin = MagicMock(
            return_value=cls.tables["volatile series"]
        )
        demand_table = {
            "electricity demand series": cls.tables[
                "electricity demand series"
            ]
        }
        demand.scenario_demand = MagicMock(return_value=demand_table)

        my_parameter = {
            "copperplate": True,
            "group_transformer": False,
            "heat": False,
            "use_variable_costs": True,
            "use_CO2_costs": True,
            "map": "de21",
        }

        my_name = "deflex"
        for k, v in my_parameter.items():
            my_name += "_" + str(k) + "-" + str(v)

        polygons = deflex_regions(rmap=my_parameter["map"], rtype="polygons")
        lines = deflex_power_lines(my_parameter["map"]).index
        base = os.path.join(os.path.expanduser("~"), ".tmp_x345234dE_deflex")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, "deflex_test{0}")
        name = "deflex_2014_de21_no-heat"
        scenario_creator.create_basic_reegis_scenario(
            name=name,
            regions=polygons,
            lines=lines,
            parameter=my_parameter,
            excel_path=path.format(".xlsx"),
            csv_path=path.format("_csv"),
        )

        sc_new = st.DeflexScenario()
        sc_new.read_csv(path.format("_csv"))
        cls.input_data = sc_new.input_data

    @classmethod
    def teardown_class(cls):
        base = os.path.join(os.path.expanduser("~"), ".tmp_x345234dE_deflex")
        shutil.rmtree(base)

    def test_volatile_source(self):
        pd.testing.assert_frame_equal(
            self.tables["volatile plants"],
            self.input_data["volatile plants"],
        )

    def test_storages(self):
        a = self.tables["electricity storages"].apply(pd.to_numeric)
        b = self.input_data["electricity storages"].apply(pd.to_numeric)
        b["energy inflow"] *= 48 / 8760
        for col in a.columns:
            pd.testing.assert_series_equal(a[col], b[col])
        # pd.testing.assert_frame_equal(a, b)

    def test_electricity_demand_series(self):
        pd.testing.assert_frame_equal(
            self.tables["electricity demand series"],
            self.input_data["electricity demand series"],
        )

    def test_transmission(self):
        pd.testing.assert_frame_equal(
            self.tables["power lines"].apply(pd.to_numeric).astype(float),
            self.input_data["power lines"].apply(pd.to_numeric),
        )

    def test_transformer(self):
        pd.testing.assert_frame_equal(
            self.tables["power plants"],
            self.input_data["power plants"],
        )

    def test_general(self):
        pd.testing.assert_series_equal(
            self.tables["general"].astype(str).sort_index(),
            self.input_data["general"].astype(str).sort_index(),
        )

    def test_commodity_source(self):
        pd.testing.assert_frame_equal(
            self.tables["commodity sources"],
            self.input_data["commodity sources"],
        )

    def test_mobility_series(self):
        pd.testing.assert_frame_equal(
            self.tables["mobility demand series"],
            self.input_data["mobility demand series"].iloc[0:48],
        )

    def test_mobility(self):
        self.input_data["mobility"]["efficiency"] = pd.to_numeric(
            self.input_data["mobility"]["efficiency"]
        )
        pd.testing.assert_frame_equal(
            self.tables["mobility"],
            self.input_data["mobility"],
        )

    def test_volatile_series(self):
        pd.testing.assert_frame_equal(
            self.tables["volatile series"],
            self.input_data["volatile series"],
        )

    def test_length(self):
        assert len(self.tables.keys()) == len(self.input_data.keys())
        assert sorted(list(self.tables.keys())) == sorted(
            list(self.input_data.keys())
        )
