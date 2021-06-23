# -*- coding: utf-8 -*-

"""
Test the postprocessing module. There are many doctests within the module.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
import pandas as pd
from oemof import solph

from deflex import postprocessing as pp
from deflex.tools import fetch_test_files


class TestReshapeBusView:
    @classmethod
    def setup_class(cls):
        fn = fetch_test_files("de21_no-heat.dflx")
        my_results = pp.restore_results(fn)

        my_buses = sorted(
            set(
                [
                    flow[0]
                    for flow in my_results["main"].keys()
                    if isinstance(flow[0], solph.Bus)
                    and flow[0].label.cat == "electricity"
                ]
            )
        )

        m_cols = pd.MultiIndex(
            levels=[[], [], [], [], []], codes=[[], [], [], [], []]
        )

        data = pd.DataFrame(columns=m_cols)

        agg1 = [
            ("cat", "line", "subtag", "all"),
            ("cat", "power plant", "tag", -1),
        ]
        agg2 = [
            ("cat", "line", "subtag", "all"),
            ("cat", "power plant", "tag", 1),
        ]

        cls.df1 = pp.reshape_bus_view(my_results, my_buses, aggregate=agg1)
        cls.df2 = pp.reshape_bus_view(my_results, my_buses)
        cls.df3 = pp.reshape_bus_view(my_results, my_buses, aggregate=agg2)
        cls.df4 = pp.reshape_bus_view(my_results, my_buses[0], data=data)

    def test_electricity_line(self):
        df1 = self.df1.groupby(level=[1, 2, 3, 4], axis=1).sum().sort_index(1)
        df2 = self.df2.groupby(level=[1, 2, 3, 4], axis=1).sum().sort_index(1)
        df3 = self.df3.groupby(level=[1, 2, 3, 4], axis=1).sum().sort_index(1)
        df4 = self.df4.groupby(level=[1, 2, 3, 4], axis=1).sum().sort_index(1)
        assert list(df1["in", "line", "electricity"].columns[:5]) == ["all"]
        assert list(df2["in", "line", "electricity"].columns[:5]) == [
            "DE01",
            "DE02",
            "DE03",
            "DE04",
            "DE05",
        ]
        assert list(df3["in", "line", "electricity"].columns[:5]) == ["all"]
        assert sorted(list(df4["in", "line", "electricity"].columns)[:5]) == [
            "DE03",
            "DE04",
            "DE13",
            "DE14",
            "DE15",
        ]

    def test_power_plants(self):
        df1 = self.df1.groupby(level=[1, 2, 3], axis=1).sum().sort_index(1)
        df2 = self.df2.groupby(level=[1, 2, 3], axis=1).sum().sort_index(1)
        df3 = self.df3.groupby(level=[1, 2, 3], axis=1).sum().sort_index(1)
        # df4 = self.df4.groupby(level=[1, 2, 3], axis=1).sum().sort_index(1)
        assert list(df1["in", "power plant"].columns[:4]) == [
            "bioenergy",
            "hard coal",
            "lignite",
            "natural gas",
        ]
        assert list(df2["in", "power plant"].columns[:4]) == [
            "bioenergy_038",
            "bioenergy_042",
            "bioenergy_045",
            "hard coal_023",
        ]
        assert list(df3["in", "power plant"].columns[:4]) == [
            "018",
            "023",
            "025",
            "027",
        ]
