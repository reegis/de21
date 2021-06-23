# -*- coding: utf-8 -*-

"""
General deflex analyses.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

from collections import namedtuple


def allocate_fuel(method, **kwargs):
    """
    Allocate the fuel input of chp plants to the two output flows: heat and
    electricity.

    The following methods are available:

    * Alternative Generation or Finnish Method -> :py:func:`finnish_method`
    * Exergy Method or Carnot Method -> :py:func:`exergy_method`
    *

    Parameters
    ----------
    method : str
        The method to allocate the output flows of chp plants:
        alternative_generation, carnot, efficiency, electricity, exergy,
        finnish, heat, iea


    Other Parameters
    ----------------
    eta_e : numeric
        The efficiency of the electricity production in the chp plant.
        Mandatory in the following functions: alternative_generation,
        exergy, iea, efficiency

    eta_th : numeric
        The efficiency of the heat output in the chp plant. Mandatory in
        the following functions: alternative_generation, exergy, iea,
        efficiency

    eta_c : numeric
        The Carnot factor of the heating system. Mandatory in
        the following functions: exergy

    eta_e_ref : numeric
        The efficiency of the best power plant available on the market and
        economically viable in the year of construction of the CHP plant.
        Mandatory in the following functions: alternative_generation

    eta_th_ref : numeric
        The efficiency of the best heat plant available on the market and
        economically viable in the year of construction of the CHP plant.
        Mandatory in the following functions: alternative_generation


    Returns
    -------
    The allocation factors of the output flows (heat/electricity): namedtuple

    Examples
    --------
    >>> a = allocate_fuel("efficiency", eta_e=0.3, eta_th=0.5)
    >>> round(a.electricity, 3)
    0.625
    >>> round(a.heat, 3)
    0.375
    >>> a = allocate_fuel("electricity")
    >>> a.electricity
    1
    >>> a.heat
    0
    >>> a = allocate_fuel("exergy", eta_e=0.3, eta_th=0.5, eta_c=0.555)
    >>> round(a.electricity, 3)
    0.519
    >>> round(a.heat, 3)
    0.481
    >>> a = allocate_fuel("finnish", eta_e=0.3, eta_th=0.5, eta_e_ref=0.5,
    ...                   eta_th_ref=0.9)
    >>> round(a.electricity, 3)
    0.519
    >>> round(a.heat, 3)
    0.481
    >>> a = allocate_fuel("heat")
    >>> a.electricity
    0
    >>> a.heat
    1
    >>> a = allocate_fuel("iea", eta_e=0.3, eta_th=0.5)
    >>> round(a.electricity, 3)
    0.375
    >>> round(a.heat, 3)
    0.625

    """
    fuel_factors = namedtuple("fuel_factors", ["heat", "electricity"])
    name = "{0} (method: {1})".format(allocate_fuel.__name__, method)

    if method == "alternative_generation" or method == "finnish":
        mandatory = ["eta_e", "eta_th", "eta_e_ref", "eta_th_ref"]
        _check_input(name, *mandatory, **kwargs)
        f_elec = finnish_method(**kwargs)
    elif method == "efficiency":
        mandatory = ["eta_e", "eta_th"]
        _check_input(name, *mandatory, **kwargs)
        f_elec = efficiency_method(**kwargs)
    elif method == "exergy" or method == "carnot":
        mandatory = ["eta_e", "eta_th", "eta_c"]
        _check_input(name, *mandatory, **kwargs)
        f_elec = exergy_method(**kwargs)
    elif method == "iea":
        mandatory = ["eta_e", "eta_th"]
        _check_input(name, *mandatory, **kwargs)
        f_elec = iea_method(**kwargs)
    elif method == "electricity":
        f_elec = 1
    elif method == "heat":
        f_elec = 0
    else:
        msg = (
            "Method '{0}' is not implemented to calculate the allocation "
            "factor of chp product flows."
        ).format(method)
        raise NotImplementedError(msg)

    return fuel_factors(heat=(1 - f_elec), electricity=f_elec)


def _check_input(name, *mandatory_parameters, **kwargs):
    """Check for mandatory parameters."""
    missing = []
    for arg in mandatory_parameters:
        if arg not in kwargs:
            missing.append(arg)
    if len(missing) > 0:
        msg = "The following parameters are missing for {0}: {1}".format(
            name, ", ".join(missing)
        )
        raise ValueError(msg)


def iea_method(eta_e, eta_th):
    r"""
    IEA Method (International Energy Association - a method to allocate the
    fuel input of chp plants to the two output flows: heat and electricity

    The allocation factor :math:`\alpha_{el}` of the electricity output is
    calculated as follows:
      .. math::
        \alpha_{el}=\frac{\eta_{el}}{\eta_{el}+\eta_{th}}

    :math:`\alpha_{el}` : Allocation factor of the electricity flow

    :math:`\eta_{el}` : Efficiency of the electricity output in the chp plant

    :math:`\eta_{th}` : Efficiency of the thermal output in the chp plant

    Parameters
    ----------
    eta_e : numeric
        The efficiency of the electricity production in the chp plant.
        Mandatory in the following functions: alternative_generation,
        exergy, iea, efficiency

    eta_th : numeric
        The efficiency of the heat output in the chp plant. Mandatory in
        the following functions: alternative_generation, exergy, iea,
        efficiency

    Returns
    -------
    Allocation factor for the electricity flow : numeric

    Examples
    --------
    >>> round(iea_method(0.3, 0.5), 3)
    0.375

    """
    return eta_e * 1 / (eta_e + eta_th)


def efficiency_method(eta_e, eta_th):
    r"""
    Efficiency Method - a method to allocate the fuel
    input of chp plants to the two output flows: heat and electricity

    The allocation factor :math:`\alpha_{el}` of the electricity output is
    calculated as follows:
      .. math::
        \alpha_{el}=\frac{\eta_{th}}{\eta_{el}+\eta_{th}}

    :math:`\alpha_{el}` : Allocation factor of the electricity flow

    :math:`\eta_{el}` : Efficiency of the electricity output in the chp plant

    :math:`\eta_{th}` : Efficiency of the thermal output in the chp plant

    Parameters
    ----------
    eta_e : numeric
        The efficiency of the electricity production in the chp plant.
        Mandatory in the following functions: alternative_generation,
        exergy, iea, efficiency

    eta_th : numeric
        The efficiency of the heat output in the chp plant. Mandatory in
        the following functions: alternative_generation, exergy, iea,
        efficiency

    Returns
    -------
    Allocation factor for the electricity flow : numeric

    Examples
    --------
    >>> round(efficiency_method(0.3, 0.5), 3)
    0.625

    """
    return eta_th / (eta_e + eta_th)


def finnish_method(eta_e, eta_th, eta_e_ref, eta_th_ref):
    r"""
    Alternative Generation or Finnish Method - a method to allocate the fuel
    input of chp plants to the two output flows: heat and electricity

    The allocation factor :math:`\alpha_{el}` of the electricity output is
    calculated as follows:
      .. math::
        \alpha_{el} = \frac{\eta_{el,ref}}{\eta_{el}} \cdot \left(
        \frac{\eta_{el}}{\eta_{el,ref}}+ \frac{\eta_{th}}{ \eta_{th,ref}}
        \right)

    :math:`\alpha_{el}` : Allocation factor of the electricity flow

    :math:`\eta_{el}` : Efficiency of the electricity output in the chp plant

    :math:`\eta_{th}` : Efficiency of the thermal output in the chp plant

    :math:`\eta_{el,ref}` : Efficiency of the reference power plant

    :math:`\eta_{th,ref}` : Efficiency of the reference heat plant


    Parameters
    ----------
    eta_e : numeric
        The efficiency of the electricity production in the chp plant.
        Mandatory in the following functions: alternative_generation,
        exergy, iea, efficiency

    eta_th : numeric
        The efficiency of the heat output in the chp plant. Mandatory in
        the following functions: alternative_generation, exergy, iea,
        efficiency

    eta_e_ref : numeric
        The efficiency of the best power plant available on the market and
        economically viable in the year of construction of the CHP plant.
        Mandatory in the following functions: alternative_generation

    eta_th_ref : numeric
        The efficiency of the best heat plant available on the market and
        economically viable in the year of construction of the CHP plant.
        Mandatory in the following functions: alternative_generation

    Returns
    -------
    Allocation factor for the electricity flow : numeric

    Examples
    --------
    >>> round(finnish_method(0.3, 0.5, 0.5, 0.9), 3)
    0.519

    """
    return (eta_e / eta_e_ref) / (eta_e / eta_e_ref + eta_th / eta_th_ref)


def exergy_method(eta_e, eta_th, eta_c):
    r"""
    Exergy Method or Carnot Method- a method to allocate the fuel
    input of chp plants to the two output flows: heat and electricity

      The allocation factor :math:`\alpha_{el}` of the electricity output is
    calculated as follows:
      .. math::
        \alpha_{el}=\frac{\eta_{el}}{\eta_{el}+\eta_{c}\cdot\eta_{th}}

    :math:`\alpha_{el}` : Allocation factor of the electricity flow

    :math:`\eta_{el}` : Efficiency of the electricity output in the chp plant

    :math:`\eta_{th}` : Efficiency of the thermal output in the chp plant

    :math:`\eta_{c}` : Carnot factor of the thermal energy


    Parameters
    ----------
    eta_e : numeric
        The efficiency of the electricity production in the chp plant.
        Mandatory in the following functions: alternative_generation,
        exergy, iea, efficiency

    eta_th : numeric
        The efficiency of the heat output in the chp plant. Mandatory in
        the following functions: alternative_generation, exergy, iea,
        efficiency

    eta_c : numeric
        The Carnot factor of the heating system. Mandatory in
        the following functions: exergy

    Returns
    -------
    Allocation factor for the electricity flow : numeric

    Examples
    --------
    >>> round(exergy_method(0.3, 0.5, 0.3), 3)
    0.667

    """
    return eta_e / (eta_e + eta_c * eta_th)
