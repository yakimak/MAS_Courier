# -*- coding: utf-8 -*-
"""
MAS-Courier: командный интерфейс.

Примеры:
    python main.py lab1
    python main.py demo --mechanism contract_net --seed 42
    python main.py lab2 --scenarios 100
    python main.py lab3 --scenarios 100
    python main.py lab4 --scenarios 100
    python main.py all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mas import generate_scenario, run_mechanism
from mas.experiments import RESULTS, run_lab2, run_lab3, run_lab4
from mas.viz import (plot_roles, plot_communication, plot_lab2,
                     plot_lab2_dashboard, plot_lab3, plot_lab3_dashboard,
                     plot_lab4, plot_lab4_dashboard, plot_routes)


def cmd_lab1(_args):
    plot_roles(RESULTS / "lab1_roles.png")
    plot_communication(RESULTS / "lab1_comm.png")
    print("Диаграммы ЛР №1 сохранены:", RESULTS)


def cmd_demo(args):
    scenario = generate_scenario(args.seed, args.orders, args.couriers,
                                 name=args.mechanism)
    result = run_mechanism(args.mechanism, scenario)
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print("\nПлан:")
    for c in scenario.couriers:
        print(f"  Курьер {c.id}: {result['plan'].get(c.id, [])}")
    print("\nСобытия (первые 10):")
    for e in result["events"][:10]:
        print(" ", e)
    plot_routes(scenario, result, RESULTS / "demo_routes.png")
    print("\nМаршруты сохранены в", RESULTS / "demo_routes.png")


def cmd_lab2(args):
    data = run_lab2(args.scenarios, args.orders, args.couriers)
    plot_lab2(data["summary"], data["rows"], RESULTS / "lab2_metrics.png")
    plot_lab2_dashboard(data["summary"], data["rows"],
                        RESULTS / "lab2_dashboard.png")
    print("ЛР №2 завершена.")
    for s in data["summary"]:
        print(f"  {s['mechanism']:<14} profit={s['profit_mean']:.1f} "
              f"SLA={s['on_time_rate_mean']:.3f} "
              f"messages={s['messages_mean']:.0f} "
              f"gini={s['gini_mean']:.3f}")


def cmd_lab3(args):
    data = run_lab3(args.scenarios, args.orders, args.couriers)
    plot_lab3(data["summary"], data["rows"], RESULTS / "lab3_comparison.png")
    plot_lab3_dashboard(data["summary"], data["rows"],
                        RESULTS / "lab3_dashboard.png")
    print("ЛР №3 завершена.")
    for s in data["summary"]:
        print(f"  {s['mechanism']:<12} profit={s['profit_mean']:.1f} "
              f"SLA={s['on_time_rate_mean']:.3f} gini={s['gini_mean']:.3f} "
              f"max_orders={s['max_orders_mean']:.2f}")


def cmd_lab4(args):
    data = run_lab4(args.scenarios, args.orders, args.couriers)
    plot_lab4(data["summary"], data["rows"], RESULTS / "lab4_resilience.png")
    plot_lab4_dashboard(data["summary"], data["rows"],
                        RESULTS / "lab4_dashboard.png")
    print("ЛР №4 завершена.")
    for s in data["summary"]:
        print(f"  {s['mode']:<10} delivered={s['delivered_mean']:.2f} "
              f"SLA={s['on_time_rate_mean']:.3f} profit={s['profit_mean']:.1f} "
              f"overhead={s['overhead_messages_mean']:.1f}")


def cmd_all(args):
    cmd_lab1(args)
    cmd_lab2(args)
    cmd_lab3(args)
    cmd_lab4(args)


def main():
    parser = argparse.ArgumentParser(description="MAS-Courier")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("lab1", help="диаграммы архитектуры")
    p1.set_defaults(func=cmd_lab1)

    p = sub.add_parser("demo", help="демонстрационный запуск")
    p.add_argument("--mechanism", default="contract_net",
                   choices=["centralized", "contract_net", "auction",
                            "fcfs", "negotiation"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--orders", type=int, default=15)
    p.add_argument("--couriers", type=int, default=5)
    p.set_defaults(func=cmd_demo)

    for name, func in [("lab2", cmd_lab2), ("lab3", cmd_lab3), ("lab4", cmd_lab4)]:
        p = sub.add_parser(name)
        p.add_argument("--scenarios", type=int, default=100)
        p.add_argument("--orders", type=int, default=15 if name == "lab2" else 16)
        p.add_argument("--couriers", type=int, default=5 if name != "lab4" else 6)
        p.set_defaults(func=func)

    p = sub.add_parser("all")
    p.add_argument("--scenarios", type=int, default=100)
    p.add_argument("--orders", type=int, default=16)
    p.add_argument("--couriers", type=int, default=5)
    p.set_defaults(func=cmd_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
