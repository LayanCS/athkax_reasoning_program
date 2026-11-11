"""Trust check, effect estimates, guardrails and break-even."""
import numpy as np
import pandas as pd
from scipy import stats

from config import Config


def srm_check(df: pd.DataFrame, expected_share_b: float, threshold: float = 0.001) -> dict:
    n_a = int((df["variant"] == "A").sum())
    n_b = int((df["variant"] == "B").sum())
    total = n_a + n_b
    chi2, p = stats.chisquare([n_a, n_b], f_exp=[total * (1 - expected_share_b), total * expected_share_b])
    return {"n_a": n_a, "n_b": n_b, "chi2": float(chi2), "p": float(p), "ok": p >= threshold}


def diff_ci(a, b, alpha: float = 0.05) -> dict:
    """Difference in means (B - A) with a normal-approximation CI and p-value."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    diff = b.mean() - a.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = stats.norm.ppf(1 - alpha / 2)
    return {
        "a": a.mean(), "b": b.mean(), "diff": diff,
        "low": diff - z * se, "high": diff + z * se, "se": se,
        "p": float(2 * stats.norm.sf(abs(diff / se))),
    }


def cuped(df: pd.DataFrame, metric: str, covariate: str = "pre_orders_90d", alpha: float = 0.05) -> dict:
    """Variance reduction using a pre-experiment covariate."""
    y, x = df[metric].astype(float), df[covariate].astype(float)
    theta = np.cov(y, x)[0, 1] / x.var(ddof=1)
    adjusted = y - theta * (x - x.mean())
    is_b = df["variant"] == "B"
    return diff_ci(adjusted[~is_b], adjusted[is_b], alpha)


def benjamini_hochberg(p_values, alpha: float = 0.05) -> np.ndarray:
    """True where a p-value stays significant after Benjamini-Hochberg correction."""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    passed = ranked <= alpha
    keep = np.zeros(len(p), dtype=bool)
    if passed.any():
        keep[order[: np.max(np.nonzero(passed)) + 1]] = True
    return keep


SECONDARY = {"order_value": "Order value (buyers only), SAR", "revenue": "Revenue per user, SAR"}

# column: (label, bad direction, tolerance)
# A guardrail is HARMED only when the whole CI is worse than the tolerance.
# With no tolerance, any tiny real increase becomes "significant" once the sample is large enough.
GUARDRAILS = {
    "profit": ("Profit per user after fees, SAR", "down", 0.0),
    "cancelled": ("Cancellation rate", "up", 0.010),       # at most +1 pt
    "contacted_support": ("Support contact rate", "up", 0.005),  # at most +0.5 pt
}


def analyse(df: pd.DataFrame, cfg: Config) -> dict:
    a, b = df[df["variant"] == "A"], df[df["variant"] == "B"]

    primary = diff_ci(a["ordered"], b["ordered"], cfg.alpha)
    primary_cuped = cuped(df, "ordered", alpha=cfg.alpha)

    secondary = {label: diff_ci(a[col], b[col], cfg.alpha) for col, label in SECONDARY.items()}
    for res, sig in zip(secondary.values(), benjamini_hochberg([r["p"] for r in secondary.values()], cfg.alpha)):
        res["significant_bh"] = bool(sig)

    guardrails = {}
    for col, (label, bad, tol) in GUARDRAILS.items():
        res = diff_ci(a[col], b[col], cfg.alpha)
        sign = -1 if bad == "down" else 1  # flip so that "worse" is always positive
        worse_low = min(sign * res["low"], sign * res["high"])
        res["harmed"] = worse_low > tol
        res["status"] = "HARMED" if res["harmed"] else ("worse, within tolerance" if worse_low > 0 else "healthy")
        guardrails[label] = res

    return {
        "srm": srm_check(df, cfg.treatment_share),
        "primary": primary,
        "primary_cuped": primary_cuped,
        "secondary": secondary,
        "guardrails": guardrails,
        "break_even": break_even(a, b, cfg),
    }


def break_even(a: pd.DataFrame, b: pd.DataFrame, cfg: Config) -> dict:
    """Conversion lift at which B earns the same profit per user as A.

    fees_only: assumes order value does not change, so every B order just pays the fee.
    observed:  uses the order values actually seen in each group.
    """
    p_a = a["ordered"].mean()
    profit_per_order_a = a.loc[a["ordered"] == 1, "profit"].mean()
    fees_only_b = profit_per_order_a - cfg.bnpl_fee_per_order
    observed_b = b.loc[b["ordered"] == 1, "profit"].mean()
    return {
        "fees_only": p_a * profit_per_order_a / fees_only_b - p_a,
        "observed": p_a * profit_per_order_a / observed_b - p_a,
        "profit_per_order_a": profit_per_order_a,
        "profit_per_order_b": observed_b,
    }
