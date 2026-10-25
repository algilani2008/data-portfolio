"""watt-wage-ksa: Saudi utility tariffs, wages and their impact.

Modules
-------
data      load the raw, sourced CSV/JSON files
tariffs   electricity and water bill calculators for every tariff schedule
household household profiles, seasonal bills, net impact after support
impact    event study of past reforms on CPI inflation
forecast  CPI baseline + tariff shock scenarios and Monte Carlo
wages     Nitaqat wage-threshold simulation
fiscal    cost of the support package vs. extra residential bill revenue
build     run everything and write outputs/ and dashboard/data.js
"""

__version__ = "1.0.0"
