"""Run the BNPL checkout experiment end to end and print a one-page report.

    python run_experiment.py                 # planned 14-day test
    python run_experiment.py --days 28       # the recommended extension
    python run_experiment.py --novelty 0.5 --srm-bug 0.02
"""
import argparse
from dataclasses import replace

from analysis import analyse
from config import Config
from decision import decide
from design import design_summary, power_at
from simulate import simulate_experiment


def pts(x: float) -> str:
    return f"{x * 100:+.2f} pts"


def ci_pts(r: dict) -> str:
    return f"{pts(r['diff'])}  [{r['low'] * 100:+.2f}, {r['high'] * 100:+.2f}]  p={r['p']:.3f}"


def ci_num(r: dict) -> str:
    return f"{r['diff']:+.2f}  [{r['low']:+.2f}, {r['high']:+.2f}]  p={r['p']:.3f}"


def report(cfg: Config, days: int | None) -> None:
    d = design_summary(cfg, days)
    df = simulate_experiment(cfg, d["days"])
    res = analyse(df, cfg)
    decision, reason = decide(res)
    p, srm, be = res["primary"], res["srm"], res["break_even"]
    profit = res["guardrails"]["Profit per user after fees, SAR"]

    print(f"\n{cfg.project}\n" + "=" * 72)

    print("\nDESIGN")
    print(f"  Needed per group:   {d['n_needed_per_group']:,} (baseline {cfg.baseline_conversion:.0%}, "
          f"MDE {cfg.mde_abs * 100:.1f} pts, power {cfg.power:.0%})")
    print(f"  Duration:           {d['days']} days, ~{d['n_expected_per_group']:,} per group")
    print(f"  Detectable effect:  {d['mde_at_days'] * 100:.2f} pts  (power at 2 pts: {d['power_at_mde']:.0%})")

    print("\nTRUST CHECK")
    print(f"  SRM: A={srm['n_a']:,}  B={srm['n_b']:,}  chi2={srm['chi2']:.2f}  p={srm['p']:.2g}  "
          f"-> {'OK' if srm['ok'] else 'MISMATCH, do not trust results'}")

    print("\nPRIMARY: checkout conversion")
    print(f"  A {p['a']:.2%}  ->  B {p['b']:.2%}")
    print(f"  Lift:         {ci_pts(p)}")
    print(f"  Lift (CUPED): {ci_pts(res['primary_cuped'])}")

    print("\nSECONDARY (Benjamini-Hochberg corrected)")
    for name, r in res["secondary"].items():
        print(f"  {name:<34} {ci_num(r)}  {'significant' if r['significant_bh'] else 'not significant'}")

    print("\nGUARDRAILS")
    for name, r in res["guardrails"].items():
        value = ci_num(r) if "SAR" in name else ci_pts(r)
        print(f"  {name:<34} {value}  {r['status']}")

    print("\nDOES IT PAY?")
    print(f"  Profit per order: A {be['profit_per_order_a']:.2f} SAR, B {be['profit_per_order_b']:.2f} SAR after fees")
    print(f"  Break-even conversion lift if order value were unchanged: {pts(be['fees_only'])}")
    print(f"  Break-even conversion lift with observed order values:    {pts(be['observed'])}")
    print(f"  Annual profit change: {profit['diff'] * cfg.annual_users / 1e6:+.2f}M SAR "
          f"[{profit['low'] * cfg.annual_users / 1e6:+.2f}, {profit['high'] * cfg.annual_users / 1e6:+.2f}]")

    print("\nDECISION (pre-registered rule)")
    print(f"  {decision}: {reason}")
    if decision == "EXTEND":
        longer = design_summary(cfg, d["days"] * 2)
        print(f"  Extending to {longer['days']} days lowers the detectable effect to {longer['mde_at_days'] * 100:.2f} pts.")

    # only possible in a simulation: compare with the hidden truth
    true_power = power_at(cfg.baseline_conversion, cfg.true_lift_abs, d["n_expected_per_group"], cfg.alpha)
    caught = p["low"] > 0
    print("\nSIMULATION CHECK (the analyst never sees this)")
    print(f"  True lift {cfg.true_lift_abs * 100:.2f} pts (novelty boost {cfg.novelty_boost}), "
          f"estimated {p['diff'] * 100:.2f} pts")
    print(f"  Power at the true lift: ~{true_power:.0%}  ->  "
          f"{'detected' if caught else 'missed (Type II error)'}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, help="experiment length (default: planned duration)")
    parser.add_argument("--seed", type=int, default=Config.seed)
    parser.add_argument("--novelty", type=float, default=Config.novelty_boost)
    parser.add_argument("--srm-bug", type=float, default=Config.srm_bug_share)
    args = parser.parse_args()
    cfg = replace(Config(), seed=args.seed, novelty_boost=args.novelty, srm_bug_share=args.srm_bug)
    report(cfg, args.days)


if __name__ == "__main__":
    main()
