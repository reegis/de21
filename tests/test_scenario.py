# -*- coding: utf-8 -*-

"""
Processing a list of power plants in Germany.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import os
import shutil

import pandas as pd
import pytest

from deflex import scenario
from deflex.tools import TEST_PATH, fetch_test_files


def test_basic_scenario_class():
    sc = scenario.Scenario()
    sc.create_nodes()


def test_scenario_building():
    sc = scenario.DeflexScenario(name="test", year=2014)
    csv_path = os.path.join(TEST_PATH, "de22_heat_transmission_csv")
    sc.read_csv(csv_path)
    sc.table2es()
    sc.check_input_data()
    sc.input_data["volatile series"].loc[5, ("DE01", "wind")] = float("nan")
    with pytest.raises(
        ValueError, match=r"NaN values found in table:'volatile series'"
    ):
        sc.check_input_data()


def test_node_dict():
    nc = scenario.NodeDict()
    nc["g"] = 5
    nc["h"] = 6
    msg = (
        "Key 'g' already exists. Duplicate keys are not allowed in a "
        "node dictionary."
    )
    with pytest.raises(KeyError, match=msg):
        nc["g"] = 7


def test_scenario_es_init():
    data = {
        "general": pd.Series(
            {"year": 2013, "name": "test", "number of time steps": 8760}
        )
    }
    sc = scenario.DeflexScenario(input_data=data)
    es1 = sc.initialise_energy_system().es
    sc = scenario.DeflexScenario(input_data=data)
    sc.input_data["general"]["year"] = 2012
    with pytest.warns(UserWarning, match="2012 is a leap year but the"):
        print(sc.initialise_energy_system().es)
    sc.input_data["general"]["number of time steps"] = 8784
    es2 = sc.initialise_energy_system().es
    assert len(es1.timeindex) == 8760
    assert len(es2.timeindex) == 8784


def test_scenario_es_init_error():
    sc = scenario.DeflexScenario()
    msg = "There is no input data in the scenario. You cannot initialise an"
    with pytest.raises(ValueError, match=msg):
        sc.initialise_energy_system()


def test_excel_reader():
    sc = scenario.DeflexScenario()
    xls_fn = fetch_test_files("de02_heat.xlsx")
    sc.read_xlsx(xls_fn)
    sc.initialise_energy_system()
    sc.table2es()
    csv_path = os.path.join(TEST_PATH, "deflex_2013_de02_tmp_X45_test_csv")
    sc.to_csv(csv_path)
    xls_fn = os.path.join(TEST_PATH, "deflex_2014_de02_tmp_X45_test")
    sc.to_xlsx(xls_fn)
    xls_fn += ".xlsx"
    sc.to_xlsx(xls_fn)
    shutil.rmtree(csv_path)
    os.remove(xls_fn)


def test_build_model():
    sc = scenario.DeflexScenario(debug=True)
    xls_fn = fetch_test_files("de02_heat.xlsx")
    sc.read_xlsx(xls_fn)
    sc.compute()
    assert sc.es.results["meta"]["name"] == "deflex_2014_de02_heat_reg-merit"


def test_build_model_manually():
    sc = scenario.DeflexScenario(debug=True)
    xls_fn = fetch_test_files("de02_no-heat.xlsx")
    sc.read_xlsx(xls_fn)
    sc.initialise_energy_system()
    test_nodes = sc.create_nodes()
    sc.add_nodes_to_es(test_nodes)
    dump_fn = os.path.join(TEST_PATH, "pytest_test")
    sc.dump(dump_fn)
    model = sc.create_model()
    sc.solve(model=model, solver="cbc", with_duals=True)
    assert (
        sc.es.results["meta"]["name"] == "deflex_2014_de02_no-heat_reg-merit"
    )
    dump_fn += ".dflx"
    sc.dump(dump_fn)
    plot_fn = os.path.join(TEST_PATH, "test_plot_X343.graphml")
    sc.plot_nodes(plot_fn)
    assert os.path.isfile(plot_fn)
    scenario.restore_scenario(dump_fn)
    assert int(sc.meta["year"]) == 2014
    os.remove(dump_fn)
    os.remove(plot_fn)


def test_corrupt_data():
    sc = scenario.DeflexScenario(year=2014)
    csv_path = os.path.join(TEST_PATH, "de03_fictive_csv")
    sc.read_csv(csv_path)
    sc.input_data["volatile series"].drop(
        ("DE02", "solar"), inplace=True, axis=1
    )
    msg = "Missing time series for solar"
    with pytest.raises(ValueError, match=msg):
        sc.table2es()


def test_restore_an_invalid_scenario():
    filename = fetch_test_files("de02_heat.xlsx")
    msg = "The suffix of a valid deflex scenario has to be '.dflx'."
    with pytest.raises(IOError, match=msg):
        scenario.restore_scenario(filename)


class TestInputDataCheck:
    @classmethod
    def setup_class(cls):
        cls.sc = scenario.DeflexScenario()
        fn = os.path.join(TEST_PATH, "de02_no-heat.xlsx")
        cls.sc.read_xlsx(fn)
        cls.sc.input_data["general"]["regions"] = float("nan")

    def test_nan_value_in_general_table_series(self):
        with pytest.raises(ValueError, match="'general'"):
            self.sc.check_input_data()

    def test_nan_values_warnings(self, recwarn):
        self.sc.input_data["volatile series"].loc[5, ("DE01", "wind")] = float(
            "nan"
        )
        self.sc.check_input_data(warning=True)
        assert len(recwarn) == 2
        assert "table:'general', column(s): Index(['regions']" in str(
            recwarn[0].message
        )
        assert (
            "table:'volatile series', column(s): (('DE01', 'wind'),)"
            in str(recwarn[1].message)
        )

    def test_wrong_length(self):
        self.sc.input_data["volatile series"] = self.sc.input_data[
            "volatile series"
        ].iloc[0:40]
        msg = "Number of time steps is 48 but the length of the volatile serie"
        with pytest.raises(ValueError, match=msg):
            self.sc.initialise_energy_system()
