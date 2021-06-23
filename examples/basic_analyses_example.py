# -*- coding: utf-8 -*-

"""
Example, which compares the calculated market clearing price (mcp) of
different de02 examples with the day ahead prices of Entsoe downloaded from
OPSD.

SPDX-FileCopyrightText: 2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import logging
import os
from datetime import datetime
from zipfile import ZipFile

import pandas as pd
import pytz
from matplotlib import pyplot as plt
from oemof.tools import logger

from deflex import tools
from deflex.tools import files as pp
from deflex.postprocessing import analyses

OPSD_URL = (
    "https://data.open-power-system-data.org/index.php?package="
    "time_series&version=2019-06-05&action=customDownload&resource=3"
    "&filter%5B_contentfilter_cet_cest_timestamp%5D%5Bfrom%5D="
    "2005-01-01&filter%5B_contentfilter_cet_cest_timestamp%5D%5Bto%5D"
    "=2019-05-01&filter%5BRegion%5D%5B%5D=DE&filter%5BVariable%5D%5B"
    "%5D=price_day_ahead&downloadCSV=Download+CSV"
)

OSF_URL = (
    "https://files.de-1.osf.io/v1/resources/a5xrj/providers/osfstorage"
    "/605c564de12b600065aa6315?action=download&direct&version=1"
)


def get_price_from_opsd(path):
    """Get day ahead prices from opsd time series."""
    fn = os.path.join(path, "opsd_day_ahead_prices.csv")
    tools.download(fn, OPSD_URL)

    de_ts = pd.read_csv(
        fn,
        index_col="utc_timestamp",
        parse_dates=True,
        date_parser=lambda col: pd.to_datetime(col, utc=True),
    )
    de_ts.index = de_ts.index.tz_convert("Europe/Berlin")
    de_ts.index.rename("cet_timestamp", inplace=True)
    berlin = pytz.timezone("Europe/Berlin")
    start_date = berlin.localize(datetime(2014, 1, 1, 0, 0, 0))
    end_date = berlin.localize(datetime(2014, 12, 31, 23, 0, 0))
    return de_ts.loc[start_date:end_date, "DE_price_day_ahead"]


# !!! ADAPT THE PATH !!!
my_path = "your/path"

# Set logger
logger.define_logging()

# Download and unzip scenarios (if zip-file does not exist)
os.makedirs(my_path, exist_ok=True)
my_fn = os.path.join(my_path, "deflex_result_examples_v03.zip")
os.makedirs(os.path.dirname(my_fn), exist_ok=True)
if not os.path.isfile(my_fn):
    tools.download(my_fn, OSF_URL)
    with ZipFile(my_fn, "r") as zip_ref:
        zip_ref.extractall(my_path)
    logging.info("All v0.3.x result examples extracted to %s.", my_path)

# Search for all de02-result-files.
result_files = pp.search_scenarios(path=my_path, map=["de02"])

# Restore the results for all found files
results = pp.restore_results(result_files)

# Create a table with the key values of a restored files
key_values = analyses.get_key_values_from_results(results)

# Store the table with the key_values
key_values_file = os.path.join(my_path, "key_values_v03.xlsx")
key_values.to_excel(key_values_file)
logging.info("Key values stored to %s.", key_values_file)

# Download Entsoe day ahead prices from OPSD
opsd = get_price_from_opsd(my_path)

# Create a new table with only the market clearing price (mcp)
mcp_file = os.path.join(my_path, "mcp_v03.xlsx")
key_values = pd.read_excel(key_values_file, header=[0, 1])
mcp = pd.DataFrame(key_values["mcp"])

# Add opsd day ahead prices to table
mcp["opsd"] = opsd.reset_index(drop=True)
mcp.set_index(opsd.index, drop=True, inplace=True)
mcp.tz_localize(None).to_excel(mcp_file)
logging.info("File with mcp stored to %s.", key_values_file)

# Read and plot the table. You can set the path to the file once it is created.
# Afterwards you will have to execute only the lines below and adapt the plot
# to your needs.

# mcp_file = "your/path"
mcp = pd.read_excel(
    mcp_file,
    index_col="cet_timestamp",
    parse_dates=True,
    date_parser=lambda col: pd.to_datetime(col, utc=False),
)

mcp.plot()
plt.show()
