Input data
----------

The input data is stored in the
:py:attr:`~deflex.scenario.Scenario.input_data` attribute of the
:py:class:`~deflex.scenario.DeflexScenario`
class (s. :ref:`deflex_scenario`). It is a dictionary with the name of the
data set as key and the data table itself as value (pandas.DataFrame or
pandas.Series).

The input data is divided into four main topics: High-level-inputs, electricity
sector, heating sector (optional) and mobility sector (optional).

Download a fictive `input data example
<https://files.de-1.osf.io/v1/resources/a5xrj/providers/osfstorage/605b1ed7818bde00cd3a6063?action=download&direct&version=1>`_
to get an idea of the structure. Then go on with the following chapter to learn
everything about how to define the data for a deflex model.

.. contents::
    :depth: 1
    :local:
    :backlinks: top


Overview
~~~~~~~~

.. image:: https://raw.githubusercontent.com/reegis/deflex/master/docs/images/spreadsheet_examples.png

A Deflex scenario can be divided into regions. Each region must have an
identifier number and be named after it as ``DEXX``, where ``XX`` is the
number. For refering the Deflex scenario as a whole (i.e. the sum of all
regions) use ``DE`` only.

At the current state the distribution of fossil fuels is neglected. Therefore,
in order to keep the computing time low it is recommended to define them
supra-regional using ``DE`` without a number. It is still possible to define
them regional for example to add a specific limit for each region.

In most cases it is also sufficient to model the fossil part of the mobility
and the decentralised heating sector supra-regional. It is assumed that a
gas boiler or a filling station is always supplied with enough fuel, so that
the only the annual values affect the model. This does not apply to electrical
heating systems or cars.

In most spread sheet software it is possible to connect cells to increase
readability. These lines are interpreted correctly. In csv files the values
have to appear in every cell. So the following two tables will be interpreted
equally!

**Connected cells**

+------+-----------+---------------+
|      |           | value         |
+------+-----------+---------------+
|      | F1        |               |
+ DE01 +-----------+---------------+
|      | F2        |               |
+------+-----------+---------------+
| DE02 | F1        |               |
+------+-----------+---------------+

**Unconnected cells**

+------+-----------+---------------+
|      |           | value         |
+------+-----------+---------------+
| DE01 | F1        |               |
+------+-----------+---------------+
| DE01 | F2        |               |
+------+-----------+---------------+
| DE02 | F1        |               |
+------+-----------+---------------+

.. note::
    NaN-values are not allowed in any table. Some columns are optional and can
    be left out, but if a column is present there have to be values in every
    row. Neutral values can be ``0``, ``1`` or ``inf``.

High-level-input (mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. contents::
    :depth: 1
    :local:
    :backlinks: top

General
+++++++

``key:`` 'general', ``value:`` `pandas.Series() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html>`_

This table contains basic data about the scenario.

+----------------------+------+
| year                 |      |
+----------------------+------+
| number of time steps |      |
+----------------------+------+
| co2 price            |      |
+----------------------+------+
| name                 |      |
+----------------------+------+

**INDEX**

year: ``int``, [-]
    A time index will be created started with January 1, at 00:00 with the
    number of hours given in `number of time steps`.
number of time steps: ``int``, [-]
    The number of hourly time steps.
co2 price: ``float``, [€/t]
    The average price for CO\ :sub:`2`  over the whole time period.
name: ``str``, [-]
    A name for the scenario. This name will be used to compare key values
    between different scenarios. Therefore, it should be unique within a group
    of scenarios. It does not have to be intuitive. Use the `info` table for
    a human readable description of your scenario.

Info
++++

``key:`` 'info', ``value:`` `pandas.Series() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html>`_

On this sheet, additional information that characterizes the scenario can be
added. The idea behind Info is that the user can filter stored scenarios using
the :py:func:`~deflex.postprocessing.search_results` function.

You can create any key-value pair which is suitable for you group of scenarios.

e.g. key: ``scenario_type`` value: ``foo`` / ``bar`` / ``foobar``

Afterwards you can search for all scenarios where the ``scenario_type`` is
``foo`` using:

.. code-block:: python

    search_results(path=my_path, scenario_type=["foo"])

or with other keys and multiple values:

.. code-block:: python

    search_results(path=my_path, scenario_type=["foo", "bar"], my_key["v1"])

The second code line will return only files with (``foo`` or ``bar``) and
``v1``.

+------+--------+
| key1 |        |
+------+--------+
| key2 |        |
+------+--------+
| key3 |        |
+------+--------+
| ...  | ...    |
+------+--------+


Commodity sources
+++++++++++++++++

``key:`` 'commodity sources', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet requires data fromm all the commodities used in the scenario. The
data can be provided either supra-regional under DE, regional under DEXX or as a
combination of both, where some commodities are global and some are regional.
Regionalised commodities are specially useful for commodities with an annual
limit, for example bioenergy.

+------+-----------+---------------+------------------+--------------------+
|      |           | costs         | emission         | annual limit       |
+------+-----------+---------------+------------------+--------------------+
|      | F1        |               |                  |                    |
+  DE  +-----------+---------------+------------------+--------------------+
|      | F2        |               |                  |                    |
+------+-----------+---------------+------------------+--------------------+
| DE01 | F1        |               |                  |                    |
+------+-----------+---------------+------------------+--------------------+
| DE02 | F2        |               |                  |                    |
+------+-----------+---------------+------------------+--------------------+
| ...  | ...       | ...           | ...              | ...                |
+------+-----------+---------------+------------------+--------------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).
level 1: ``str``
    Fuel type.

**COLUMNS**

costs: ``float``, [€/MWh]
    The fuel production cost.

emission: ``float``, [t/MWh]
    The fuel emission factor.
    
annual limit: ``float``, [MWh]
    The annual maximum energy generation (if there is one, otherwise just use
    *inf*). If the ``annual limit`` is ``inf`` in every line the column can be
    left out.


Data sources
++++++++++++

``key:`` 'data sources', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

*Highly recomended*. Here the type data, the source name and the url from where
they were obtained can be listed. It is a free format and additional columns
can be added. This table helps to make your scenario as transparent as
possible.

+-----------+--------------+---------+-----+-----+
|           | source       | url     | v1  | ... |
+-----------+--------------+---------+-----+-----+
| cost data | Institute    | http1   | a1  | ... |
+-----------+--------------+---------+-----+-----+
| pv plants | Organisation | http2   | a2  | ... |
+-----------+--------------+---------+-----+-----+
| ...       | ...          | ...     | ... | ... |
+-----------+--------------+---------+-----+-----+


Electricity sector (mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. contents::
    :depth: 1
    :local:
    :backlinks: top

Electricity demand series
+++++++++++++++++++++++++

``key:`` 'electricity demand series',
``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet requires the electricity demand of the scenario as a time series. One summarised demand series for each region is enough, but it
is possible to distinguish between different types. This will not have any
effect on the model results but may help to distinguish the different flows in
the results.

+-------------+----------+----------+-----------+----------+----------+-----+
|             |   DE01   |            DE02                 | DE03     | ... |
+-------------+----------+----------+-----------+----------+----------+-----+
|             | all      | indsutry | buildings | rest     | all      | ... |
+-------------+----------+----------+-----------+----------+----------+-----+
| Time step 1 |          |          |           |          |          | ... |
+-------------+----------+----------+-----------+----------+----------+-----+
| Time step 2 |          |          |           |          |          | ... |
+-------------+----------+----------+-----------+----------+----------+-----+
| ...         | ...      | ...      | ...       | ...      | ...      | ... |
+-------------+----------+----------+-----------+----------+----------+-----+

**INDEX**

time step: ``int``
    Number of time step. Must be uniform in all series tables.

**COLUMNS**

unit: ``[MW]``

level 0: ``str``
    Region (e.g. DE01, DE02).

level 1: ``str``
    Specification of the series e.g. "all" for an overall series.


Power plants
++++++++++++

``key:`` 'power plants', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

The power plants will feed in the electricity bus of the region the are
located. The data must be divided by region and subdivided by fuel. Each row
can indicate one power plant or a group of power plants. It is possible to add
additional columns for information purposes.

+-------+------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
|       |      | capacity | fuel | efficiency | annual electricity limit | variable_cost | downtime_factor | source_region |
+-------+------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
|       | N1   |          |      |            |                          |               |                 |               |
+       +------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
| DE01  | N2   |          |      |            |                          |               |                 |               |
+       +------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
|       | N3   |          |      |            |                          |               |                 |               |
+-------+------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
| DE02  | N2   |          |      |            |                          |               |                 |               |
+       +------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
|       | N3   |          |      |            |                          |               |                 |               |
+-------+------+----------+------+------------+--------------------------+---------------+-----------------+---------------+
| ...   | ...  | ...      |...   | ...        | ...                      | ...           | ...             | ...           |
+-------+------+----------+------+------------+--------------------------+---------------+-----------------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02).
level 1: ``str``
    Name, arbitrary. The combination of region and name is the unique
    identifier for the power plant or the group of power plants.

**COLUMNS**

capacity: ``float``, [MW]
    The installed capacity of the power plant or the group of power plants.

fuel: ``str``, [-]
    The used fuel of the power plant or group of power plants. The combination
    of `source_region` and `fuel` must exist in the commodity sources table.

efficiency: ``float``, [-]
    The average overall efficiency of the power plant or the group of power
    plants.

annual limit: ``float``, [MWh]
    The absolute maximum limit of produced electricity within the whole
    modeling period.

variable_costs: ``float``, [€/MWh]
    The variable costs per produced electricity unit.

downtime_factor: ``float``, [-]
    The time fraction of the modeling period in which the power plant or the
    group of power plants cannot produce electricity. The installed capacity
    will be reduced by this factor ``capacity * (1 - downtime_factor)``.

source_region, [-]
    The source region of the fuel source. Typically this is the region of the
    index or ``DE`` if it is a global commodity source. The combination of
    `source_region` and `fuel` must exist in the commodity sources table.


Volatiles plants
++++++++++++++++

``key:`` 'volatile plants', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Examples of volatile power plants are solar, wind, hydro, geothermal. Data
must be provided divided by region and subdivided by energy source. Each row
can indicate one plant or a group of plants. It is possible to add additional
columns for information purposes.

+------+------+---------------+
|      |      | capacity      |
+------+------+---------------+
| DE01 | N1   |               |
+------+------+---------------+
|      | N2   |               |
+------+------+---------------+
| DE02 | N1   |               |
+------+------+---------------+
| DE03 | N1   |               |
+------+------+---------------+
|      | N3   |               |
+------+------+---------------+
| ...  | ...  | ...           |
+------+------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02).
level 1: ``str``
    Name, arbitrary. The combination of the region and the name has to exist as
    a time series in the `volatile series` table.
    
**COLUMNS**

capacity: ``float``, [MW]
    The installed capacity of the plant.


Volatile series
+++++++++++++++

``key:`` 'volatile series', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet provides the normalised feed-in time series in
MW/MW :sub:`installed`. So each time series will multiplied with its installed
capacity to get the absolute feed-in. Therefore, the combination of region and
name has to exist in the `volatile plants` table.

+-------------+------+-----+------+------+-----+-----+
|             |     DE01   | DE02 |    DE03    | ... |
+-------------+------+-----+------+------+-----+-----+
|             | N1   | N2  | N1   | N1   | N3  | ... |
+-------------+------+-----+------+------+-----+-----+
| Time step 1 |      |     |      |      |     | ... |
+-------------+------+-----+------+------+-----+-----+
| Time step 2 |      |     |      |      |     | ... |
+-------------+------+-----+------+------+-----+-----+
| ...         | ...  | ... | ...  | ...  | ... | ... |
+-------------+------+-----+------+------+-----+-----+

**INDEX**

time step: ``int``
    Number of time step. Must be uniform in all series tables.

**COLUMNS**

unit: ``[MW]``

level 0: ``str``
    Region (e.g. DE01, DE02).

level 1: ``str``
    Name of the energy source specified in the previous sheet.


    
Power lines
+++++++++++

``key:`` 'power lines', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

The power lines table defines the connection between the electricity buses of
each region of the scenario. There is no default connection. If no connection
is defined the regions will be self-sufficient.

+-----------+---------------+------------+
|           | capacity      | efficiency |
+-----------+---------------+------------+
| DE01-DE02 |               |            |
+-----------+---------------+------------+
| DE01-DE03 |               |            |
+-----------+---------------+------------+
| DE02-DE03 |               |            |
+-----------+---------------+------------+
| ...       | ...           | ...        |
+-----------+---------------+------------+

**INDEX**

Name: ``str``
    Name of the 2 connected regions separated by a dash. Define only one
    direction. In the model one line for each direction will be created. If
    both directions are defined in the table two lines for each direction will
    be created for the model, so that the capacity will be the sum of both
    lines.


**COLUMNS**

capacity: ``float``, [MW]
    The maximum transmission capacity of the power lines.
    
efficiency:``float``, [-]
    The transmission efficiency of the power line.
    
Electricity storages
++++++++++++++++++++

``key:`` 'storages', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Electricity storages is a particular case of storages (see
`Storages`_). The condition to use a storage as electrcitiy storage
is to use storage medium = electricity.


Heating sector (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. contents::
    :depth: 1
    :local:
    :backlinks: top

Heat demand series
++++++++++++++++++

``key:`` 'heat demand series', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

The heat demand can be entered regionally under DEXX or supra-regional under DE.
The only type of demand that must be entered regionally is district heating.
As recommendation, coal, gas, or oil demands should be treated supra-regional.

+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+
|             |       DE01             | DE02                         |     |       DE        |
+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+
|             | district heating | N1  | district heating | N1  | N2  | ... | N3  | N4  | N5  |
+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+
| Time step 1 |                  |     |                  |     |     |     |     |     |     |
+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+
| Time step 2 |                  |     |                  |     |     |     |     |     |     |
+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+
| ...         | ...              | ... | ...              | ... | ... | ... | ... | ... | ... |
+-------------+------------------+-----+------------------+-----+-----+-----+-----+-----+-----+

**INDEX**

time step: ``int``
    Number of time step. Must be uniform in all series tables.

**COLUMNS**

unit: ``[MW]``

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).

level 1: ``str``
    Name. Specification of the series e.g. `district heating`, `coal`, `gas`.
    Except for `district heating` each combination of region and name must
    exist in the `decentralised heat` table.



Decentralised heat
++++++++++++++++++

``key:`` 'decentralised heat', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet covers all heating technologies that are used to generate
decentralized heat. In this context decentralised does not mean regional it
represents the large group of independent heating systems. If there is no
specific reason to define a heating system regional they should be defined supra-regional.

+------+------+------------+--------+---------------+
|      |      | efficiency | source | source region |
+------+------+------------+--------+---------------+
| DE01 | N1   |            |        | DE01          |
+------+------+------------+--------+---------------+
| DE02 | N1   |            |        | DE02          |
|      +------+------------+--------+---------------+
|      | N2   |            |        | DE02          |
+------+------+------------+--------+---------------+
|      | ...  |            |        | ...           |
+------+------+------------+--------+---------------+
| DE   | N3   |            |        | DE            |
|      +------+------------+--------+---------------+
|      | N4   |            |        | DE            |
|      +------+------------+--------+---------------+
|      | N5   |            |        | DE            |
+------+------+------------+--------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).
level 1: ``str``
    Name, arbitrary.

**COLUMNS**

efficiency: ``float``, [-]
    The efficiency of the heating technology.
    
source: ``str``, [-]
    The source that the heating technology uses. Examples are coal, oil for
    commodities, but it could also be electricity in case of a heat pump.
    Except for `electricity` the combination of `source` and `source region`
    has to exist in the `commodity sources` table. The `electricity` source
    will be connected to the electricity bus of the region defined in
    `source region`.

source region: ``str``
    The region where the source comes from (see `source`).


Chp - heat plants
+++++++++++++++++

``key:`` 'chp-heat plants', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet covers CHP and heat plants. Each plant will feed into the
`district heating` bus of the region it it is located. The demand of
`district heating` is defined in the `heat demand series` table with the name
`district heating`. All plants of the same region with the same fuel can be
defined in one row but it is also possible to divide them by additional
categories such as efficiency etc.

+------+------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      |      | limit heat chp | capacity heat chp | capacity elec chp | limit hp | capacity hp | efficiency hp | efficiency heat chp | efficiency elec chp | fuel | source region |
+------+------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
| DE01 | N1   |                |                   |                   |          |             |               |                     |                     |      | DE01          |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N3   |                |                   |                   |          |             |               |                     |                     |      | DE            |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N4   |                |                   |                   |          |             |               |                     |                     |      | DE            |
+------+------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
| DE02 | N1   |                |                   |                   |          |             |               |                     |                     |      | DE02          |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N2   |                |                   |                   |          |             |               |                     |                     |      | DE02          |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N3   |                |                   |                   |          |             |               |                     |                     |      | DE            |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N4   |                |                   |                   |          |             |               |                     |                     |      | DE            |
|      +------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
|      | N5   |                |                   |                   |          |             |               |                     |                     |      | DE            |
+------+------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+
| ...  | ...  | ...            | ...               | ...               | ...      | ...         | ...           | ...                 | ...                 | ...  | ...           |
+------+------+----------------+-------------------+-------------------+----------+-------------+---------------+---------------------+---------------------+------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02).
level 1: ``str``
    Name, arbitrary.

**COLUMNS**

limit heat chp: ``float``, [MWh]
    The absolute maximum limit of heat produced by chp within the whole
    modeling period.
    
capacity heat chp: ``float``, [MW]
    The installed heat capacity of all chp plants of the same group in the
    region.
    
capacity elect chp: ``float``, [MW]
    The installed electricity capacity of all chp plants of the same group in
    the region.

limit hp: ``float``, [MWh]
    The absolute maximum limit of heat produced by the heat plant within the
    whole modeling period.
    
capacity hp: ``float``, [MW]
    The installed heat capacity of all heat of the same group in the region.
    
efficiency hp: ``float``, [-]
    The average overall efficiency of the heat plant.
    
efficiency heat chp: ``float``, [-]
    The average overall heat efficiency of the chp.
    
efficiency elect chp: ``float``, [-]
    The average overall electricity efficiency of the chp.

fuel: ``str``, [-]
    The used fuel of the plants. The fuel name must be equal to the fuel
    type of the commodity sources. The combination of `fuel` and
    `source region` has to exist in the `commodity sources` table.

source_region, [-]
    The source region of the fuel source. Typically this is the region of the
    index or ``DE`` if it is a global commodity source.


Mobility sector (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. contents::
    :depth: 1
    :local:
    :backlinks: top

Mobility demand series
++++++++++++++++++++++
``key:`` 'mobility series', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

The mobility demand can be entered regionally or supra-regional. However, it is
recommended to define the mobility demand supra-regional except for
`electricity`. The demand for electric mobility has be defined regional because
it will be connected to the electricity bus of each region. The combination of
region and name has to exist in the `mobility` table.

+-------------+-------------+-------------+-----+-----+
|             |     DE01    | DE02        | ... | DE  |
+-------------+-------------+-------------+-----+-----+
|             | electricity | electricity |     | N1  |
+-------------+-------------+-------------+-----+-----+
| Time step 1 |             |             |     |     |
+-------------+-------------+-------------+-----+-----+
| Time step 2 |             |             |     |     |
+-------------+-------------+-------------+-----+-----+
| ...         | ...         | ...         | ... | ... |
+-------------+-------------+-------------+-----+-----+

**INDEX**

time step: ``int``
    Number of time step. Must be uniform in all series tables.

**COLUMNS**

unit: ``[MW]``

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).

level 1: ``str``
    Specification of the series e.g. "electricity" for each region or "diesel",
    "petrol" for DE.



Mobility
++++++++
``key:`` 'mobility', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

This sheet covers the technologies of the mobility sector.

+------+-------------+------------+--------------------+---------------+
|      |             | efficiency | source             | source region |
+------+-------------+------------+--------------------+---------------+
| DE01 | electricity |            | electricity        | DE01          |
+------+-------------+------------+--------------------+---------------+
| DE02 | electricity |            | electricity        | DE02          |
+------+-------------+------------+--------------------+---------------+
| ...  |             |            |                    |               |
+------+-------------+------------+--------------------+---------------+
| DE   | N1          |            | oil/biofuel/H2/etc | DE            |
+------+-------------+------------+--------------------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).
level 1: ``str``
    Name, arbitrary.

**COLUMNS**

efficiency: ``float``, [-]
    The efficiency of the fuel production. If a `diesel` demand is defined in
    the `mobility demand series` table the `efficiency` represents the
    efficiency of `diesel` production from the commodity source e.g. oil. For
    a `biofuel` demand the efficiency of the production of `biofuel` from
    `biomass` has to be defined.
    
source: ``str``, [-]
    The source that the technology uses. Except for `electricity` the
    combination of `source` and `source region` has to exist in the
    `commodity sources` table. The `electricity` source will be connected to
    the electricity bus of the region defined in `source region`.

source region: ``str``, [-]
    The region where the source comes from.
    

Other (optional)
~~~~~~~~~~~~~~~~

.. contents::
    :depth: 1
    :local:
    :backlinks: top


Storages
++++++++

``key:`` 'storages', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Different type of storages can be defined in this table. All different
storage technologies (pumped hydro, batteries, compressed air, hydrogen, etc) have to be
entered in a general way. Each row can indicate one storage or a group of
storages. If the storage medium is electricity, then the storage must exist in a region DEXX. Otherwise, the storage can be defined under DE. It is possible to add additional columns for information purposes.

+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
|      |      | storage medium | energy content | energy inflow | charge capacity | discharge capacity | charge efficiency | discharge efficiency | loss rate |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
| DE01 | S1   | electricity    |                |               |                 |                    |                   |                      |           |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
|      | S2   | electricity    |                |               |                 |                    |                   |                      |           |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
| DE02 | S1   | electricity    |                |               |                 |                    |                   |                      |           |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
| DE   | S3   | hydrogen       |                |               |                 |                    |                   |                      |           |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+
| ...  | ...  | ...            | ...            | ...           | ...             | ...                | ...               | ...                  | ...       |
+------+------+----------------+----------------+---------------+-----------------+--------------------+-------------------+----------------------+-----------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02).
level 1: ``str``
    Name, arbitrary.
    
**COLUMNS**

storage medium: ``str``
    The medium used to store energy. The storage medium must be defined in commodities, or it must be electricity.

energy content: ``float``, [MWh]
    The maximum energy content of a storage or a group storages.

energy inflow: ``float``, [MWh]
    The amount of energy that will feed into the storage of the model period in
    MWh. For example a river into a pumped hydroelectric energy storage.
    
charge capacity: ``float``, [MW]
    Maximum capacity to charge the storage or the group of storages.
    
discharge capacity: ``float``, [MW]
    Maximum capacity to discharge the storage or the group of storages.

charge efficiency: ``float``, [-]
    Charging efficiency of the storage or the group of storages.
    
discharge efficiency: ``float``, [-]
    Discharging efficiency of the storage or the group of storages.
    
loss rate: ``float``, [-]
    The relative loss of the energy content of the storage. For example a loss
    rate or `0.01` means that the energy content of the storage will be
    reduced by `1%` in each time step.

Other converters
++++++++++++++++

``key:`` 'other converters', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Here, other converters than the ones already set, can be defined for linking different buses. A good example here is an electrolyser which connects electricity with hydrogen. Each converter has a source and a target bus with their respective regions. Other converter´s format is analogous to that of power plants and heat plants.

+------+---------------+----------+--------------+------------+----------------+-----------------+-------------+---------------+----------+---------------+
|      |               | capacity | annual limit | efficiency | variable costs | downtime factor | source      | source region | target   | target region |
+------+---------------+----------+--------------+------------+----------------+-----------------+-------------+---------------+----------+---------------+
| DE   | electrolyser1 |          |              |            |                |                 | electricity | DE01          | hydrogen | DE            |
+------+---------------+----------+--------------+------------+----------------+-----------------+-------------+---------------+----------+---------------+
| DE   | electrolyser2 |          |              |            |                |                 | electricity | DE02          | hydrogen | DE            |
+------+---------------+----------+--------------+------------+----------------+-----------------+-------------+---------------+----------+---------------+
| DE01 | C1            |          |              |            |                |                 | S1          | DE01          | T1       | DE01          |
+------+---------------+----------+--------------+------------+----------------+-----------------+-------------+---------------+----------+---------------+

**INDEX**

level 0: ``str``
    Region (e.g. DE01, DE02).
level 1: ``str``
    Name, arbitrary. The combination of region and name is the unique
    identifier for the converter or the group of converters.

**COLUMNS**

capacity: ``float``, [MW]
    The installed capacity of the converter or the group of converters.

annual limit: ``float``, [MWh]
    The absolute maximum limit of produced target units within the whole
    modeling period.
    
efficiency: ``float``, [-]
    The average overall efficiency of the converter or the group of converters.
    
variable_costs: ``float``, [€/MWh]
    The variable costs per produced target unit.
    
downtime_factor: ``float``, [-]
    The time fraction of the modeling period in which the converter or the
    group of converters cannot produce target units. The installed capacity
    will be reduced by this factor ``capacity * (1 - downtime_factor)``.

source: ``str``, [-]
    The source bus of the converter or group of converters. The combination
    of `source_region` and `source` must exist in the commodity sources table or it can be electricity with its region DEXX.


source_region, [-]
    The source region of the source. Typically this is the region of the
    index or ``DE`` if it is a global commodity source.
    
target: ``str``, [-]
    The target bus of the converter or group of converters. The combination
    of `target_region` and `target` must exist in the commodity sources table or it can be electricity with its region DEXX.


trget_region, [-]
    The target region of the target. Typically this is the region of the
    index or ``DE`` if it is a global commodity target.
    
Other demand series
+++++++++++++++++++

``key:`` 'other demand series', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Here, other demands different from electricity, heat or mobility can be entered as time series. Examples are hydrogen or synthetic fuel for the industry sector.
The demands can be entered regionally under DEXX or supra-regional under DE. The format here is analogous to that of electricity, heat and mobility demand series.


+-------------+---------------------+---------------------+---------------------+
|             |         DE01        |         DE02        |          DE         |
+-------------+----------+----------+----------+----------+----------+----------+
|             |    D1    |    D2    |    D1    |    D3    | hydrogen | syn fuel |
+-------------+----------+----------+----------+----------+----------+----------+
|             | sector 1 | sector 1 | sector 2 | sector 3 | industry | industry |
+-------------+----------+----------+----------+----------+----------+----------+
| Time step 1 |          |          |          |          |          |          |
+-------------+----------+----------+----------+----------+----------+----------+
| Time step 2 |          |          |          |          |          |          |
+-------------+----------+----------+----------+----------+----------+----------+
| ...         | ...      | ...      | ...      | ...      | ...      | ...      |
+-------------+----------+----------+----------+----------+----------+----------+

**INDEX**

time step: ``int``
    Number of time step. Must be uniform in all series tables.

**COLUMNS**

unit: ``[MW]``

level 0: ``str``
    Region (e.g. DE01, DE02 or DE).

level 1: ``str``
    Name. Specification of the series e.g. `hydrogen`, `syn fuel`.

level 2: ``str``
    Sector name. Specification of the series e.g. `industry`, `LULUCF`. This extra level is used to differentiate the sector in which the commodity is used, since the same commodity may be used in different sectors.
    



Demand response
++++++++++++++++++++

``key:`` 'demand response', ``value:`` `pandas.DataFrame() <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_

Demand response, also known as demand side management is used to represent flexibility in the demand time series. Because of that it is applied on the four different demand series. There is the option of using two different methods of demand response: the interval and the delay one. The documentation of both methods con be found in  `SinkDSM <https://oemof-solph.readthedocs.io/en/latest/usage.html#oemof-solph-custom-sinkdsm-label>`_ where the interval method corresponds to "oemof" and the delay to "DIW" method. Depending on whether the interval or delay method is used, the shift interval or delay columns must be used. Finally, there is also the option of adding a price to use this feature.

+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           |      |             |          | capacity up | capacity down |  method  | shift interval | delay | cost up | cost down |
+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|   mobility demand series  | DE01 | electricity |   None   |             |               | interval | 8              | 0     |         |           |
|                           +------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           | DE02 | electricity |   None   |             |               | interval | 8              | 0     |         |           |
|                           +------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           |  DE  |     oil     |   None   |             |               |   delay  | 0              | 10    |         |           |
+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
| electricity demand series | DE01 |     all     |   None   |             |               | interval | 8              | 0     |         |           |
|                           +------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           | DE02 | indsutry    |   None   |             |               | interval | 8              | 0     |         |           |
|                           +------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           | DE02 | buildings   |   None   |             |               | interval | 8              | 0     |         |           |
+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
| heat demand series        | DE01 | heat pump   |   None   |             |               | interval | 6              | 0     |         |           |
|                           +------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
|                           | DE   | natural gas |   None   |             |               | delay    | 6              | 0     |         |           |
+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+
| other demand series       | DE   | hydrogen    | indsutry |             |               | delay    | 0              | 12    |         |           |
+---------------------------+------+-------------+----------+-------------+---------------+----------+----------------+-------+---------+-----------+


**INDEX**

level 0: ``str``
    Name of the demand serie.
level 1: ``str``
    Region (e.g. DE01, DE02 or DE)
level 2: ``str``
    Specification of the serie. The combination of `region` and
    `specification of the serie` has to exist in the corresponding `demand serie` sheet.
level 3: ``str``
    Sector name. This extra index is for when `other demand series` is used. If this is not the case, just write `None` instead.

**COLUMNS**

capacity up: ``float``, [MW]
    The maximum limit with respect to the demand, to which the demand can be increased.

capacity down: ``float``, [MW]
    The minimum limit with respect to the demand, to which the demand can be reduced.

method: ``str``, [-]
    The method chosen to be used.

shift interval: ``str``, [-]
    If the interval method is used, this column indicates the maximum interval that the demand can be shifted.

delay: ``str``, [-]
    If the deelay method is used, this column indicates the maximum delay that demand can be shifted.
    
cost up: ``float``, [€/MWh]
    The variable costs per shifted up unit

cost down: ``float``, [€/MWh]
    The variable costs per shifted down unit.
    


