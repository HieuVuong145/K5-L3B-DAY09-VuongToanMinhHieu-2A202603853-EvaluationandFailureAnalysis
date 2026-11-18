"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems = []

    # 1. Any metric value in pr["metrics"] that is NaN or inf
    for m, val in pr.get("metrics", {}).items():
        if isinstance(val, (int, float)) and (math.isnan(val) or math.isinf(val)):
            problems.append(f"metric {m} has non-finite value: {val}")

    # 2. len(pr["rows"]) != manifest items x len(manifest seeds)
    manifest = pr.get("manifest", {})
    expected_rows = manifest.get("items", 0) * len(manifest.get("seeds", []))
    if len(pr.get("rows", [])) != expected_rows:
        problems.append(f"row count {len(pr.get('rows', []))} != manifest expected {expected_rows}")

    # 3. the (item_id, seed) set of PR differs from the baseline's
    pr_pairs = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_pairs = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_pairs != base_pairs:
        problems.append("PR (item_id, seed) set differs from baseline")

    # 4. pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is None
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s)")

    spec_graded_ids = [m["id"] for m in spec.get("metrics", []) if m.get("grader")]
    for r in pr.get("rows", []):
        for mid in spec_graded_ids:
            if mid in r and r[mid] is None:
                problems.append(f"item {r.get('item_id')}@seed {r.get('seed')} has None for graded metric {mid}")
                break
        if problems and problems[-1].startswith("item "):
            break

    # 5. slice tags in PR rows differ from baseline's
    pr_slices = {r.get("item_id"): tuple(sorted(r.get("slices") or [])) for r in pr.get("rows", [])}
    base_slices = {r.get("item_id"): tuple(sorted(r.get("slices") or [])) for r in base.get("rows", [])}
    for item_id, tags in pr_slices.items():
        if item_id in base_slices and tags != base_slices[item_id]:
            problems.append(f"slice tags for item {item_id} differ from baseline")
            break

    # 6. base_spec ratchet: thresholds in spec cannot be looser than base_spec on same eval_set_version
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_m_map = {m["id"]: m for m in base_spec.get("metrics", [])}
        spec_m_map = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, bm in base_m_map.items():
            if mid not in spec_m_map:
                problems.append(f"ratchet: metric {mid} was removed from spec")
                continue
            sm = spec_m_map[mid]
            if bm.get("blocking") and not sm.get("blocking"):
                problems.append(f"ratchet: metric {mid} became non-blocking")
            b_th = bm.get("threshold", {})
            s_th = sm.get("threshold", {})
            if "min" in b_th and ("min" not in s_th or s_th["min"] < b_th["min"]):
                problems.append(f"ratchet: metric {mid} min threshold loosened ({s_th.get('min')} < {b_th['min']})")
            if "max" in b_th and ("max" not in s_th or s_th["max"] > b_th["max"]):
                problems.append(f"ratchet: metric {mid} max threshold loosened ({s_th.get('max')} > {b_th['max']})")
            if "max_increase" in b_th and ("max_increase" not in s_th or s_th["max_increase"] > b_th["max_increase"]):
                problems.append(f"ratchet: metric {mid} max_increase loosened")
            if b_th.get("no_significant_drop") and not s_th.get("no_significant_drop"):
                problems.append(f"ratchet: metric {mid} dropped no_significant_drop")

        base_s_map = {f"{s['name']}/{s['metric']}": s for s in base_spec.get("slices", [])}
        spec_s_map = {f"{s['name']}/{s['metric']}": s for s in spec.get("slices", [])}
        for sid, bs_slice in base_s_map.items():
            if sid not in spec_s_map:
                problems.append(f"ratchet: slice {sid} was removed")
                continue
            ss_slice = spec_s_map[sid]
            if bs_slice.get("blocking") and not ss_slice.get("blocking"):
                problems.append(f"ratchet: slice {sid} became non-blocking")
            if "min" in bs_slice and ("min" not in ss_slice or ss_slice["min"] < bs_slice["min"]):
                problems.append(f"ratchet: slice {sid} min threshold loosened")
            if bs_slice.get("no_significant_drop") and not ss_slice.get("no_significant_drop"):
                problems.append(f"ratchet: slice {sid} dropped no_significant_drop")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked = []
    lines = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name = s["name"]
        metric = s["metric"]
        min_val = s.get("min")
        blocking = s.get("blocking", True)

        pr_by_item = per_item(pr, metric, slice_name=name)
        if not pr_by_item:
            continue
        val = sum(pr_by_item.values()) / len(pr_by_item)

        verdict = "ok"
        note = ""

        if min_val is not None and val < min_val:
            verdict = "fail"

        if s.get("no_significant_drop"):
            base_by_item = per_item(base, metric, slice_name=name)
            keys = sorted(set(pr_by_item) & set(base_by_item))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_by_item[k] for k in keys],
                    [base_by_item[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        sid = f"slice:{name}/{metric}"
        if verdict != "ok" and blocking:
            blocked.append(sid)
        label = "BLOCK" if (verdict != "ok" and blocking) else ("warn" if verdict != "ok" else "ok")
        lines.append(f"  {sid:<30} {val:<8.4f} min={min_val!s:<6} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
