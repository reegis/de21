# -*- coding: utf-8 -*-

"""
Example, which shows two different ways of solving a deflex scenario.

SPDX-FileCopyrightText: 2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""


import logging
import os
from zipfile import ZipFile

from oemof.tools import logger

from deflex import main
from deflex import scenario
from deflex import tools

url = (
    "https://files.de-1.osf.io/v1/resources/a5xrj/providers/osfstorage"
    "/605c566be12b600065aa635f?action=download&direct&version=1"
)

# !!! ADAPT THE PATH !!!
path = "your/path"

# Set logger
logger.define_logging()

# Download and unzip scenarios (if zip-file does not exist)
os.makedirs(path, exist_ok=True)
fn = os.path.join(path, "deflex_scenario_examples_v03.zip")
if not os.path.isfile(fn):
    tools.download(fn, url)
with ZipFile(fn, "r") as zip_ref:
    zip_ref.extractall(path)
logging.info("All v0.3.x scenarios examples extracted to %s.", path)

# Look in your folder above. You should see some scenario files. The csv and
# the xlsx scenarios are the same. The csv-directories can be read faster by
# the computer but the xlsx-files are easier to read for humans because all
# sheets are in one file.

# NOTE: Large models will need up to 24 GB of RAM, so start with small models
# and increase the size step by step. You can also use large models with less
# time steps but you have to adapt the annual limits.

# Now choose one example. We will start with a small one:
file = "deflex_2014_de02_no-heat_csv"
fn = os.path.join(path, file)

# *** Long version ***

# Create a scenario object
sc = scenario.DeflexScenario()

# Read the input data. Use the right method (csv/xlsx) for your file type.
sc.read_csv(fn)
# sc.read_xlsx(fn)

# Create the LP model and solve it.
sc.compute()

# Dump the results to a sub-dir named "results_cbc".
dump_file = file.replace("_csv", ".dflx")
# dump_file = file.replace(".xlsx")
dump_path = os.path.join(path, "results_cbc", dump_file)
sc.dump(dump_path)

# *** short version ***

main.model_scenario(fn, file_type="csv")
