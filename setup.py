#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ) as fh:
        return fh.read()


setup(
    name="deflex",
    version="0.3.1dev0",
    license="MIT",
    description=(
        "deflex - flexible multi-regional energy system model for "
        "heat, power and mobility"
    ),
    long_description="%s\n%s"
    % (
        re.compile("^.. start-badges.*^.. end-badges", re.M | re.S).sub(
            "", read("README.rst")
        ),
        re.sub(":[a-z]+:`~?(.*?)`", r"``\1``", read("CHANGELOG.rst")),
    ),
    long_description_content_type="text/x-rst",
    author="Uwe Krien",
    author_email="krien@uni-bremen.de",
    url="https://github.com/reegis/deflex",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
    project_urls={
        "Documentation": "https://deflex.readthedocs.io/",
        "Changelog": "https://deflex.readthedocs.io/en/latest/changelog.html",
        "Issue Tracker": "https://github.com/reegis/deflex/issues",
    },
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires=">=3.7",
    install_requires=[
        "oemof.solph > 0.4",
        "oemof.network",
        "pandas > 1.0",
        "requests",
        "networkx > 2.0",
        "numpy >= 1.19.4",
        "openpyxl >= 1.3.0",
        "dill >= 0.3.3",
    ],
    extras_require={
        "dev": [
            "pytest",
            "sphinx",
            "sphinx_rtd_theme",
            "requests",
            "pygeos",
            "geopandas",
            "coveralls",
            "scenario_builder",
            "reegis",
            "matplotlib",
            "sphinx-autoapi",
        ],
        "plot": ["pygraphviz", "matplotlib"],
        "scenario": ["scenario_builder", "reegis"],
        "geo": ["pygeos", "geopandas", "descartes"],
        "example": [
            "matplotlib",
            "requests",
            "pytz",
        ],
        "dummy": ["oemof"],
    },
    package_data={
        "deflex": [
            join("data", "static", "*.csv"),
            join("data", "static", "*.txt"),
            join("data", "geometries", "*.csv"),
            join("data", "geometries", "*.geojson"),
            "*.ini",
        ]
    },
)
