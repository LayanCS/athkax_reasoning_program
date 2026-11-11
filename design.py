"""Sample size, duration, minimum detectable effect and power for a two-proportion test."""
import math

from scipy import stats

from config import Config


def _z(alpha: float, power: float) -> tuple[float, float]:
    return stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)


def sample_size_per_group(p: float, mde: float, alpha: float, power: float) -> int:
    z_a, z_b = _z(alpha, power)
    p2 = p + mde
    variance = p * (1 - p) + p2 * (1 - p2)
    return math.ceil((z_a + z_b) ** 2 * variance / mde ** 2)


def mde(p: float, n_per_group: int, alpha: float, power: float) -> float:
    z_a, z_b = _z(alpha, power)
    return (z_a + z_b) * math.sqrt(2 * p * (1 - p) / n_per_group)


def power_at(p: float, effect: float, n_per_group: int, alpha: float) -> float:
    """Approximate chance of a significant two-sided result for a true effect of this size."""
    se = math.sqrt(2 * p * (1 - p) / n_per_group)
    return float(stats.norm.cdf(abs(effect) / se - stats.norm.ppf(1 - alpha / 2)))


def duration_days(n_per_group: int, daily_users: int, share: float, whole_weeks: bool = True) -> int:
    """Days until the smaller group reaches n_per_group, rounded up to full weeks."""
    days = math.ceil(n_per_group / (daily_users * min(share, 1 - share)))
    return math.ceil(days / 7) * 7 if whole_weeks else days


def design_summary(cfg: Config, days: int | None = None) -> dict:
    n_needed = sample_size_per_group(cfg.baseline_conversion, cfg.mde_abs, cfg.alpha, cfg.power)
    planned_days = duration_days(n_needed, cfg.daily_users, cfg.treatment_share)
    days = days or planned_days
    n_expected = int(days * cfg.daily_users * min(cfg.treatment_share, 1 - cfg.treatment_share))
    return {
        "n_needed_per_group": n_needed,
        "planned_days": planned_days,
        "days": days,
        "n_expected_per_group": n_expected,
        "mde_at_days": mde(cfg.baseline_conversion, n_expected, cfg.alpha, cfg.power),
        "power_at_mde": power_at(cfg.baseline_conversion, cfg.mde_abs, n_expected, cfg.alpha),
    }
