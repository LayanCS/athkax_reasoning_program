"""The decision rule written in the analysis plan before any data was seen."""

SHIP, KILL, EXTEND, STOP = "SHIP", "KILL", "EXTEND", "STOP"


def decide(results: dict) -> tuple[str, str]:
    srm, primary = results["srm"], results["primary"]
    harmed = [name for name, g in results["guardrails"].items() if g["harmed"]]

    if not srm["ok"]:
        return STOP, f"Sample ratio mismatch (p = {srm['p']:.2g}); find the bug before reading results."
    if harmed:
        return KILL, "A guardrail got significantly worse: " + ", ".join(harmed) + "."
    if primary["low"] > 0:
        return SHIP, "Conversion lift is positive and significant, and no guardrail is beyond its tolerance."
    if primary["diff"] <= 0:
        return KILL, "Conversion lift is zero or negative."
    return EXTEND, "Conversion lift is positive but not significant, and no guardrail is beyond its tolerance."
