# -*- coding: utf-8 -*-
"""Визуализация архитектуры и результатов экспериментов MAS-Courier."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

RESULTS = Path(__file__).resolve().parent.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float_rows(rows, keys):
    for r in rows:
        for k in keys:
            r[k] = float(r[k])
    return rows


# ---------------------------------------------------------------------------
# ЛР №1: диаграммы
# ---------------------------------------------------------------------------
def plot_roles(path: Path):
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    def box(x, y, w, h, title, lines, color):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.15",
                           linewidth=1.6, edgecolor="#2C3E50", facecolor=color)
        ax.add_patch(p)
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top",
                fontsize=11, fontweight="bold", color="#12263A")
        ax.text(x + w / 2, y + h - 0.62, "\n".join(lines), ha="center", va="top",
                fontsize=8.3, color="#1B2631")

    def arrow(x1, y1, x2, y2, label="", color="#2F5D8A"):
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                            linewidth=1.4, color=color,
                            connectionstyle="arc3,rad=0.0")
        ax.add_patch(a)
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, fontsize=7.5,
                    color=color, ha="center")

    ax.text(7, 8.7, "Диаграмма ролей MAS-Courier", ha="center", va="center",
            fontsize=15, fontweight="bold", color="#12263A")

    box(0.6, 5.7, 3.4, 2.3, "OrderAgent (заказ)",
        ["Цель: доставить заказ вовремя", "Знания: адреса, окно, приоритет",
         "Действия: создать заказ,", "подтвердить доставку"], "#D6EAF8")
    box(5.2, 5.7, 3.6, 2.3, "DispatcherAgent",
        ["Цель: максимизировать качество", "и загрузку курьеров",
         "Знания: заказы, курьеры,", "правила координации",
         "Действия: CFP, назначение,", "арбитраж"], "#FCF3CF")
    box(10.0, 5.7, 3.4, 2.3, "CourierAgent",
        ["Цель: выполнить маршрут", "с максимальной полезностью",
         "Знания: capacity, ETA,", "репутация, стоимость",
         "Действия: bid, accept,", "report, negotiate"], "#D5F5E3")

    box(0.6, 2.2, 3.4, 2.3, "MonitorAgent",
        ["Цель: аудит и надёжность", "Знания: трассы, KPI, репутация",
         "Действия: detect, validate,", "quarantine, sanction"], "#FADBD8")
    box(5.2, 2.2, 3.6, 2.3, "MapServiceAgent",
        ["Цель: маршрутизация", "Знания: граф города, пробки",
         "Действия: shortest_path,", "ETA, fallback"], "#E8DAEF")
    box(10.0, 2.2, 3.4, 2.3, "Environment",
        ["Городская сетка 4×3", "Заказы, курьеры, время", "Среда симуляции"],
        "#EAECEE")

    arrow(4.0, 6.9, 5.2, 6.9, "заказ / статус")
    arrow(8.8, 6.9, 10.0, 6.9, "CFP / award")
    arrow(10.0, 6.1, 8.8, 6.1, "proposal / status")
    arrow(7.0, 5.7, 4.0, 4.5, "трассы")
    arrow(5.8, 4.5, 3.5, 5.7, "санкции")
    arrow(7.0, 5.7, 7.0, 4.5, "ETA / path")
    arrow(6.8, 2.2, 6.8, 1.7, "")
    ax.text(7.0, 1.45, "Среда задаёт расстояния и ограничения",
            ha="center", fontsize=8, color="#566573")

    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_communication(path: Path):
    G = nx.DiGraph()
    roles = ["OrderAgent", "DispatcherAgent", "CourierAgent",
             "MonitorAgent", "MapServiceAgent"]
    for r in roles:
        G.add_node(r)
    edges = [
        ("OrderAgent", "DispatcherAgent", "REQUEST"),
        ("DispatcherAgent", "OrderAgent", "CONFIRM"),
        ("DispatcherAgent", "CourierAgent", "CFP"),
        ("CourierAgent", "DispatcherAgent", "PROPOSE"),
        ("DispatcherAgent", "CourierAgent", "ACCEPT"),
        ("CourierAgent", "DispatcherAgent", "INFORM(status)"),
        ("CourierAgent", "MonitorAgent", "REPORT"),
        ("MonitorAgent", "DispatcherAgent", "ALERT"),
        ("DispatcherAgent", "MapServiceAgent", "QUERY"),
        ("MapServiceAgent", "DispatcherAgent", "ETA"),
    ]
    for u, v, label in edges:
        G.add_edge(u, v, label=label)
    pos = nx.circular_layout(G)
    fig, ax = plt.subplots(figsize=(10, 8))
    nx.draw_networkx_nodes(G, pos, node_size=3200,
                           node_color=["#D6EAF8", "#FCF3CF", "#D5F5E3",
                                       "#FADBD8", "#E8DAEF"],
                           edgecolors="#2C3E50", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8.5, ax=ax)
    nx.draw_networkx_edges(G, pos, arrowstyle="-|>", arrowsize=14,
                           edge_color="#2F5D8A", width=1.3,
                           connectionstyle="arc3,rad=0.08", ax=ax)
    labels = {(u, v): d["label"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=7,
                                 label_pos=0.35, ax=ax)
    ax.set_title("Граф коммуникаций и FIPA-подобные перформативы",
                 fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# ЛР №2
# ---------------------------------------------------------------------------
def plot_lab2(summary: List[dict], rows: List[dict], path: Path):
    from matplotlib.gridspec import GridSpec

    mechs = [r["mechanism"] for r in summary]
    colors = {"centralized": "#2F5D8A", "contract_net": "#27AE60",
              "auction": "#C0392B"}
    labels = {"centralized": "Централизованный", "contract_net": "Контрактная сеть",
              "auction": "Аукцион"}
    metrics = [("profit", "Прибыль"), ("on_time_rate", "Доля вовремя"),
               ("messages", "Число сообщений"), ("gini", "Gini нагрузки")]
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.28)
    fig.suptitle("ЛР №2 · Сравнение механизмов распределения заказов",
                 fontsize=16, fontweight="bold", color="#12263A")
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        means = [next(r for r in summary if r["mechanism"] == m)[f"{key}_mean"]
                 for m in mechs]
        stds = [next(r for r in summary if r["mechanism"] == m)[f"{key}_std"]
                for m in mechs]
        bars = ax.bar([labels[m] for m in mechs], means, yerr=stds, capsize=5,
                      color=[colors[m] for m in mechs], alpha=0.85)
        for bar, v in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
        ax.tick_params(axis="x", rotation=12)
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_lab2_dashboard(summary, rows, path):
    from matplotlib.gridspec import GridSpec

    mechs = ["centralized", "contract_net", "auction"]
    labels = {"centralized": "Централизованный", "contract_net": "Контрактная сеть",
              "auction": "Аукцион"}
    colors = ["#2F5D8A", "#27AE60", "#C0392B"]
    fig = plt.figure(figsize=(17, 10.5))
    gs = GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.28)
    fig.suptitle("ЛР №2 · Механизмы распределения задач в MAS-Courier",
                 fontsize=16, fontweight="bold", color="#12263A", y=0.98)

    ax = fig.add_subplot(gs[0, :2])
    data = [[r["profit"] for r in rows if r["mechanism"] == m] for m in mechs]
    bp = ax.boxplot(data, patch_artist=True, tick_labels=[labels[m] for m in mechs])
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.72)
    ax.set_ylabel("Прибыль")
    ax.set_title("Распределение прибыли по 100 сценариям")
    ax.grid(alpha=0.3, axis="y")

    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis("off")
    lines = ["Средние значения", ""]
    for m in mechs:
        s = next(r for r in summary if r["mechanism"] == m)
        lines += [labels[m],
                  f"  прибыль: {s['profit_mean']:.1f}",
                  f"  SLA: {s['on_time_rate_mean']:.3f}",
                  f"  сообщений: {s['messages_mean']:.0f}",
                  f"  Gini: {s['gini_mean']:.3f}", ""]
    ax2.text(0.02, 0.98, "\n".join(lines), ha="left", va="top", fontsize=9.5,
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#EAF2FB", edgecolor="#2F5D8A"))

    metrics = [("profit", "Средняя прибыль"), ("on_time_rate", "Средний SLA"),
               ("messages", "Среднее число сообщений")]
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[1, i])
        means = [next(r for r in summary if r["mechanism"] == m)[f"{key}_mean"]
                 for m in mechs]
        stds = [next(r for r in summary if r["mechanism"] == m)[f"{key}_std"]
                for m in mechs]
        bars = ax.bar([labels[m].split()[0] for m in mechs], means, yerr=stds,
                      capsize=4, color=colors, alpha=0.85)
        for bar, v in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=12)
        ax.grid(alpha=0.3, axis="y")
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# ЛР №3
# ---------------------------------------------------------------------------
def plot_lab3(summary, rows, path):
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.28)
    fig.suptitle("ЛР №3 · Переговоры и разрешение конфликтов",
                 fontsize=16, fontweight="bold", color="#12263A")
    metrics = [("profit", "Прибыль"), ("on_time_rate", "SLA"),
               ("gini", "Неравенство (Gini)"), ("max_orders", "Макс. заказов на курьера")]
    colors = {"fcfs": "#C0392B", "negotiation": "#27AE60"}
    labels = {"fcfs": "До (FCFS)", "negotiation": "После (переговоры)"}
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        means = [next(r for r in summary if r["mechanism"] == m)[f"{key}_mean"]
                 for m in ["fcfs", "negotiation"]]
        stds = [next(r for r in summary if r["mechanism"] == m)[f"{key}_std"]
                for m in ["fcfs", "negotiation"]]
        bars = ax.bar([labels[m] for m in ["fcfs", "negotiation"]], means,
                      yerr=stds, capsize=5,
                      color=[colors["fcfs"], colors["negotiation"]], alpha=0.85)
        for bar, v in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_lab3_dashboard(summary, rows, path):
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(17, 10.5))
    gs = GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.28)
    fig.suptitle("ЛР №3 · Переговоры: эффективность, справедливость, SLA",
                 fontsize=16, fontweight="bold", color="#12263A", y=0.98)
    metrics = [("profit", "Прибыль"), ("on_time_rate", "SLA"),
               ("gini", "Gini"), ("max_orders", "Заказов/курьер"),
               ("messages", "Сообщения"), ("rounds", "Раунды переговоров")]
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        means = [next(r for r in summary if r["mechanism"] == m)[f"{key}_mean"]
                 for m in ["fcfs", "negotiation"]]
        stds = [next(r for r in summary if r["mechanism"] == m)[f"{key}_std"]
                for m in ["fcfs", "negotiation"]]
        ax.bar(["до", "после"], means, yerr=stds, capsize=4,
               color=["#C0392B", "#27AE60"], alpha=0.85)
        for j, v in enumerate(means):
            ax.text(j, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# ЛР №4
# ---------------------------------------------------------------------------
def plot_lab4(summary, rows, path):
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.28)
    fig.suptitle("ЛР №4 · Диверсионный анализ и надёжность MAS",
                 fontsize=16, fontweight="bold", color="#12263A")
    metrics = [("delivered", "Доставлено заказов"), ("on_time_rate", "SLA"),
               ("profit", "Прибыль"), ("messages", "Сообщения")]
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        means = [next(r for r in summary if r["mode"] == m)[f"{key}_mean"]
                 for m in ["baseline", "defended"]]
        stds = [next(r for r in summary if r["mode"] == m)[f"{key}_std"]
                for m in ["baseline", "defended"]]
        ax.bar(["без защиты", "с защитой"], means, yerr=stds, capsize=5,
               color=["#C0392B", "#27AE60"], alpha=0.85)
        for j, v in enumerate(means):
            ax.text(j, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_lab4_dashboard(summary, rows, path):
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(17, 10.5))
    gs = GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.28)
    fig.suptitle("ЛР №4 · Устойчивость MAS-Courier к неблагоприятным сценариям",
                 fontsize=16, fontweight="bold", color="#12263A", y=0.98)
    metrics = [("delivered", "Доставлено"), ("on_time_rate", "SLA"),
               ("profit", "Прибыль"), ("overhead_messages", "Накладные сообщения"),
               ("detection_time", "Время обнаружения, мин"),
               ("detected_faults", "Обнаружено fault'ов")]
    for i, (key, title) in enumerate(metrics):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        means = [next(r for r in summary if r["mode"] == m)[f"{key}_mean"]
                 for m in ["baseline", "defended"]]
        ax.bar(["без", "с защитой"], means, color=["#C0392B", "#27AE60"], alpha=0.85)
        for j, v in enumerate(means):
            ax.text(j, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# Карта маршрутов (демонстрация)
# ---------------------------------------------------------------------------
def plot_routes(scenario, result, path):
    g = scenario.graph
    fig, ax = plt.subplots(figsize=(9, 7))
    for (u, v), _ in g.dist.items():
        if u < v and abs(g.travel_time(u, v) - 4.0) < 1e-9:
            x1, y1 = g.coords[u]
            x2, y2 = g.coords[v]
            ax.plot([x1, x2], [y1, y2], color="#D5D8DC", lw=2, zorder=1)
    colors = plt.cm.tab10(np.linspace(0, 1, len(scenario.couriers)))
    orders = {o.id: o for o in scenario.orders}
    for k, c in enumerate(scenario.couriers):
        route = result["plan"].get(c.id, [])
        xs, ys = [g.coords[c.start][0]], [g.coords[c.start][1]]
        for oid in route:
            o = orders[oid]
            for node in (o.pickup, o.delivery):
                x, y = g.coords[node]
                xs.append(x)
                ys.append(y)
        ax.plot(xs, ys, "-o", color=colors[k], lw=1.5, ms=4,
                label=f"Курьер {c.id} ({len(route)} зак.)", alpha=0.8)
    for i, (x, y) in g.coords.items():
        ax.scatter(x, y, s=180, color="#F9E79F", edgecolor="#2C3E50", zorder=3)
        ax.text(x, y, str(i), ha="center", va="center", fontsize=8, zorder=4)
    ax.set_title("Маршруты курьеров (демонстрационный сценарий)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
