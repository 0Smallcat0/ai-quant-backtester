"""
Standard Stress Testing Scenarios
This module defines common historical market stress periods for validating strategy robustness.
"""

STRESS_SCENARIOS = {
    "COVID_19_CRASH": ("2020-02-19", "2020-03-23"),
    "TECH_BEAR_2022": ("2021-11-19", "2022-12-28"),
    "INFLATION_SHOCK_2022": ("2022-01-01", "2022-06-30"),
    "BANKING_CRISIS_2023": ("2023-03-01", "2023-04-01"),
}
