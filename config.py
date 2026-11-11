"""Experiment settings.

DESIGN values are known (or estimated) before the experiment starts.
SIMULATION values are the hidden "truth" used to generate data; in a real
experiment the analyst never sees them.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    project: str = "Does adding Buy Now, Pay Later (BNPL) at checkout increase sales?"

    # ---- design ----
    baseline_conversion: float = 0.45   # current checkout completion rate
    mde_abs: float = 0.020              # smallest lift that changes the decision (2 points)
    alpha: float = 0.05
    power: float = 0.80
    daily_users: int = 2_000            # new users reaching checkout per day
    treatment_share: float = 0.5
    annual_users: int = 730_000         # 2,000/day x 365, used to annualise profit
    margin: float = 0.25                # gross margin before payment fees
    bnpl_fee_per_order: float = 1.6     # ~30% adoption x 4% provider fee x 130 SAR

    # ---- simulation truth (hidden) ----
    true_lift_abs: float = 0.015        # deliberately below the MDE
    order_value_mean: float = 130.0
    order_value_sd: float = 60.0
    order_value_effect: float = 10.0    # instalments make bigger baskets easier
    cancel_rate: float = 0.05
    cancel_effect: float = 0.005
    support_rate: float = 0.03
    support_effect: float = 0.003
    activity_strength: float = 0.8      # how strongly past activity predicts buying
    novelty_boost: float = 0.0          # extra early lift that fades (0.5 = +50% on day 1)
    srm_bug_share: float = 0.0          # >0 drops low-activity users from B (a logging bug)
    seed: int = 2026
