"""Repeat the simulated experiment many times to see how often each decision comes out.

One run can be lucky or unlucky. This shows what the 14-day design and the
28-day extension decide across many runs of the same hidden truth.

    python power_check.py --runs 500
"""
import argparse
from collections import Counter

from analysis import analyse
from config import Config
from decision import decide
from design import design_summary
from simulate import simulate_experiment


def check(cfg: Config, days: int, runs: int) -> None:
    outcomes = Counter()
    for seed in range(runs):
        df = simulate_experiment(cfg, days, seed=seed)
        outcomes[decide(analyse(df, cfg))[0]] += 1
    mde = design_summary(cfg, days)["mde_at_days"]
    shares = "  ".join(f"{k} {outcomes[k] / runs:5.1%}" for k in ("SHIP", "EXTEND", "KILL", "STOP"))
    print(f"  {days:>2} days (MDE {mde * 100:.2f} pts):  {shares}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=300)
    args = parser.parse_args()
    cfg = Config()
    print(f"\nTrue lift {cfg.true_lift_abs * 100:.1f} pts, {args.runs} runs each. SHIP = detected.")
    for days in (14, 28):
        check(cfg, days, args.runs)
    print()


if __name__ == "__main__":
    main()
