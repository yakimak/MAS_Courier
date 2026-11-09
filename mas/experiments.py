# -*- coding: utf-8 -*-
"""Экспериментальные сценарии для лабораторных работ №2–№4."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from scipy.stats import mannwhitneyu

from .faults import inject_faults
from .model import generate_scenario
from .protocols import run_mechanism

RESULTS = Path(__file__).resolve().parent.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, rows: List[dict], header: List[str] | None = None):
    if not rows:
        return
    header = header or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def _summary(rows: List[dict], group_key: str, metrics: List[str]) -> List[dict]:
    groups = sorted({r[group_key] for r in rows})
    out = []
    for g in groups:
        sub = [r for r in rows if r[group_key] == g]
        row = {group_key: g, "n": len(sub)}
        for m in metrics:
            vals = np.array([r[m] for r in sub], dtype=float)
            row[f"{m}_mean"] = float(vals.mean())
            row[f"{m}_std"] = float(vals.std())
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# ЛР №2: сравнение механизмов распределения задач
# ---------------------------------------------------------------------------
def run_lab2(n_scenarios: int = 100, n_orders: int = 15,
             n_couriers: int = 5) -> dict:
    mechanisms = ["centralized", "contract_net", "auction"]
    rows = []
    for seed in range(n_scenarios):
        scenario = generate_scenario(seed, n_orders, n_couriers)
        for mech in mechanisms:
            result = run_mechanism(mech, scenario)
            m = result["metrics"]
            rows.append({
                "scenario": seed, "mechanism": mech,
                "profit": m["profit"], "reward": m["reward"],
                "delivered": m["delivered"], "failed": m["failed"],
                "on_time_rate": m["on_time_rate"], "sla": m["sla"],
                "makespan": m["makespan"], "late_minutes": m["late_minutes"],
                "messages": m["messages"],
                "coordination_cost": m["coordination_cost"],
                "gini": m["gini"], "utilization": m["utilization"],
                "avg_delivery_time": m["avg_delivery_time"],
            })
    _write_csv(RESULTS / "lab2_scenarios.csv", rows)
    metrics = ["profit", "on_time_rate", "makespan", "messages",
               "coordination_cost", "gini", "utilization", "late_minutes"]
    summary = _summary(rows, "mechanism", metrics)
    _write_csv(RESULTS / "lab2_summary.csv", summary)

    # статистические сравнения
    tests = []
    for a, b in [("centralized", "contract_net"), ("centralized", "auction"),
                 ("contract_net", "auction")]:
        for metric in ["profit", "on_time_rate", "gini", "messages"]:
            va = [r[metric] for r in rows if r["mechanism"] == a]
            vb = [r[metric] for r in rows if r["mechanism"] == b]
            try:
                p = float(mannwhitneyu(va, vb, alternative="two-sided").pvalue)
            except ValueError:
                p = float("nan")
            tests.append({"mechanism_a": a, "mechanism_b": b,
                          "metric": metric, "p_value": p})
    _write_csv(RESULTS / "lab2_tests.csv", tests)
    return {"rows": rows, "summary": summary, "tests": tests}


# ---------------------------------------------------------------------------
# ЛР №3: переговоры и разрешение конфликтов
# ---------------------------------------------------------------------------
def run_lab3(n_scenarios: int = 100, n_orders: int = 16,
             n_couriers: int = 5) -> dict:
    rows = []
    for seed in range(n_scenarios):
        scenario = generate_scenario(seed, n_orders, n_couriers,
                                     name="conflict")
        for mech in ["fcfs", "negotiation"]:
            result = run_mechanism(mech, scenario)
            m = result["metrics"]
            max_orders = max((len(r) for r in result["plan"].values()), default=0)
            rows.append({
                "scenario": seed, "mechanism": mech,
                "profit": m["profit"], "reward": m["reward"],
                "delivered": m["delivered"], "failed": m["failed"],
                "on_time_rate": m["on_time_rate"], "sla": m["sla"],
                "gini": m["gini"], "max_orders": max_orders,
                "messages": m["messages"],
                "coordination_cost": m["coordination_cost"],
                "rounds": result.get("negotiation_rounds", 0),
                "makespan": m["makespan"],
            })
    _write_csv(RESULTS / "lab3_scenarios.csv", rows)
    metrics = ["profit", "on_time_rate", "gini", "max_orders",
               "messages", "coordination_cost", "rounds", "makespan"]
    summary = _summary(rows, "mechanism", metrics)
    _write_csv(RESULTS / "lab3_summary.csv", summary)

    tests = []
    for metric in ["profit", "on_time_rate", "gini", "max_orders"]:
        a = [r[metric] for r in rows if r["mechanism"] == "fcfs"]
        b = [r[metric] for r in rows if r["mechanism"] == "negotiation"]
        try:
            p = float(mannwhitneyu(a, b, alternative="two-sided").pvalue)
        except ValueError:
            p = float("nan")
        tests.append({"metric": metric, "p_value": p})
    _write_csv(RESULTS / "lab3_tests.csv", tests)
    return {"rows": rows, "summary": summary, "tests": tests}


# ---------------------------------------------------------------------------
# ЛР №4: диверсионный анализ и надёжность
# ---------------------------------------------------------------------------
def run_lab4(n_scenarios: int = 100, n_orders: int = 18,
             n_couriers: int = 6) -> dict:
    rows = []
    trace_sample = None
    for seed in range(n_scenarios):
        scenario = generate_scenario(seed, n_orders, n_couriers)
        base = run_mechanism("contract_net", scenario)
        for defense in [False, True]:
            res = inject_faults(scenario, base, defense=defense)
            m = res["metrics"]
            rows.append({
                "scenario": seed,
                "mode": "defended" if defense else "baseline",
                "delivered": m["delivered"], "failed": m["failed"],
                "on_time_rate": m["on_time_rate"], "sla": m["sla"],
                "profit": m["profit"],
                "messages": m["messages"],
                "overhead_messages": m["overhead_messages"],
                "detection_time": m["detection_time"],
                "detected_faults": m["detected"],
                "faults": ";".join(m["faults"]),
                "false_positive_rate": m["false_positive_rate"],
            })
            if seed == 0 and defense:
                trace_sample = res
    _write_csv(RESULTS / "lab4_scenarios.csv", rows)
    metrics = ["delivered", "on_time_rate", "profit", "messages",
               "overhead_messages", "detection_time", "detected_faults"]
    summary = _summary(rows, "mode", metrics)
    _write_csv(RESULTS / "lab4_summary.csv", summary)

    tests = []
    for metric in ["delivered", "on_time_rate", "profit"]:
        a = [r[metric] for r in rows if r["mode"] == "baseline"]
        b = [r[metric] for r in rows if r["mode"] == "defended"]
        try:
            p = float(mannwhitneyu(a, b, alternative="two-sided").pvalue)
        except ValueError:
            p = float("nan")
        tests.append({"metric": metric, "p_value": p})
    _write_csv(RESULTS / "lab4_tests.csv", tests)

    if trace_sample is not None:
        with open(RESULTS / "lab4_trace_sample.json", "w", encoding="utf-8") as f:
            json.dump({"faults": trace_sample["faults"],
                       "events": trace_sample["events"],
                       "metrics": trace_sample["metrics"]},
                      f, ensure_ascii=False, indent=2, default=float)
    return {"rows": rows, "summary": summary, "tests": tests,
            "trace": trace_sample}
