"""Generate one row per user who reaches checkout during the experiment."""
import numpy as np
import pandas as pd

from config import Config


def simulate_experiment(cfg: Config, days: int, seed: int | None = None) -> pd.DataFrame:
    r = np.random.default_rng(cfg.seed if seed is None else seed)
    n = days * cfg.daily_users

    is_b = (r.random(n) < cfg.treatment_share).astype(int)
    day = r.integers(1, days + 1, n)
    activity = r.normal(0, 1, n)  # latent; the analyst only sees pre_orders_90d

    # baseline purchase probability, rescaled so its mean equals the baseline rate
    base = cfg.baseline_conversion
    p0 = 1 / (1 + np.exp(-(np.log(base / (1 - base)) + cfg.activity_strength * activity)))
    p0 = np.clip(p0 * base / p0.mean(), 0, 1)
    pre_orders_90d = r.poisson(5 * p0 / base)

    lift = cfg.true_lift_abs * (1 + cfg.novelty_boost * np.exp(-(day - 1) / 3))
    ordered = r.binomial(1, np.clip(p0 + lift * is_b, 0, 1))

    value = np.maximum(10, r.normal(cfg.order_value_mean + cfg.order_value_effect * is_b, cfg.order_value_sd))
    revenue = ordered * value
    profit = ordered * (cfg.margin * value - cfg.bnpl_fee_per_order * is_b)
    cancelled = np.where(
        ordered == 1, r.binomial(1, np.clip(cfg.cancel_rate + cfg.cancel_effect * is_b, 0, 1)), np.nan
    )
    support = r.binomial(1, np.clip(cfg.support_rate + cfg.support_effect * is_b, 0, 1))

    df = pd.DataFrame({
        "variant": np.where(is_b == 1, "B", "A"),
        "day": day,
        "pre_orders_90d": pre_orders_90d,
        "ordered": ordered,
        "order_value": np.where(ordered == 1, value, np.nan),
        "revenue": revenue,
        "profit": profit,
        "cancelled": cancelled,
        "contacted_support": support,
    })

    if cfg.srm_bug_share > 0:  # logging bug: some low-activity B users never get recorded
        lost = (df["variant"] == "B") & (activity < 0) & (r.random(n) < cfg.srm_bug_share * 2)
        df = df[~lost]
    return df.reset_index(drop=True)
