# -*- coding: utf-8 -*-
"""
MAS-Courier: предметная модель и базовая симуляция.

Город — сетка 4×3 (12 узлов). Заказы — доставка «ресторан → клиент».
Курьеры — агенты с грузоподъёмностью, стоимостью минуты, надёжностью и
сменой. Все времена — в минутах.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

SERVICE_TIME = 3.0          # минут на погрузку/разгрузку
MSG_COST = 0.15             # условная стоимость одного сообщения


# ---------------------------------------------------------------------------
# Граф города
# ---------------------------------------------------------------------------
class CityGraph:
    def __init__(self, cols: int = 4, rows: int = 3, edge_minutes: float = 4.0):
        self.cols, self.rows = cols, rows
        self.n_nodes = cols * rows
        self.coords = {i: (i % cols, i // cols) for i in range(self.n_nodes)}
        self.adj: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(self.n_nodes)}
        for i in range(self.n_nodes):
            x, y = self.coords[i]
            if x + 1 < cols:
                j = i + 1
                self._add_edge(i, j, edge_minutes)
            if y + 1 < rows:
                j = i + cols
                self._add_edge(i, j, edge_minutes)
        self.dist, self.path = self._all_pairs()

    def _add_edge(self, u: int, v: int, w: float):
        self.adj[u].append((v, w))
        self.adj[v].append((u, w))

    def _dijkstra(self, src: int):
        dist = {i: math.inf for i in range(self.n_nodes)}
        prev = {i: None for i in range(self.n_nodes)}
        dist[src] = 0.0
        pq = [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u] + 1e-12:
                continue
            for v, w in self.adj[u]:
                nd = d + w
                if nd < dist[v] - 1e-12:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def _all_pairs(self):
        dist, path = {}, {}
        for s in range(self.n_nodes):
            d, prev = self._dijkstra(s)
            for t in range(self.n_nodes):
                dist[(s, t)] = d[t]
                if s == t:
                    path[(s, t)] = [s]
                else:
                    seq, cur = [], t
                    while cur is not None:
                        seq.append(cur)
                        cur = prev[cur]
                    path[(s, t)] = list(reversed(seq))
        return dist, path

    def travel_time(self, u: int, v: int) -> float:
        return self.dist[(u, v)]


# ---------------------------------------------------------------------------
# Заказы и курьеры
# ---------------------------------------------------------------------------
@dataclass
class Order:
    id: int
    pickup: int
    delivery: int
    ready: float
    deadline: float
    priority: int
    weight: float
    reward: float


@dataclass
class Courier:
    id: int
    start: int
    capacity: float
    speed: float
    cost_per_min: float
    reliability: float
    shift_end: float
    reputation: float = 0.8


@dataclass
class Scenario:
    name: str
    seed: int
    graph: CityGraph
    orders: List[Order]
    couriers: List[Courier]
    meta: dict = field(default_factory=dict)


def generate_scenario(seed: int, n_orders: int = 15, n_couriers: int = 5,
                      name: str = "base") -> Scenario:
    rng = np.random.default_rng(seed)
    g = CityGraph()
    orders = []
    for oid in range(n_orders):
        pickup = int(rng.integers(0, g.n_nodes))
        delivery = int(rng.integers(0, g.n_nodes - 1))
        if delivery >= pickup:
            delivery += 1
        ready = float(rng.integers(0, 45))
        window = float(rng.integers(35, 110))
        priority = int(rng.choice([1, 2, 3], p=[0.45, 0.35, 0.20]))
        weight = float(rng.integers(1, 6))
        reward = float(80 + 60 * priority + rng.integers(0, 60))
        orders.append(Order(oid, pickup, delivery, ready, ready + window,
                            priority, weight, reward))

    couriers = []
    for cid in range(n_couriers):
        couriers.append(Courier(
            id=cid,
            start=int(rng.integers(0, g.n_nodes)),
            capacity=float(rng.integers(8, 15)),
            speed=float(rng.uniform(0.85, 1.15)),
            cost_per_min=float(rng.uniform(0.8, 1.5)),
            reliability=float(rng.uniform(0.80, 0.99)),
            shift_end=float(rng.integers(240, 361)),
            reputation=float(rng.uniform(0.65, 0.95)),
        ))
    return Scenario(name=name, seed=seed, graph=g, orders=orders,
                    couriers=couriers, meta={"n_orders": n_orders,
                                             "n_couriers": n_couriers})


# ---------------------------------------------------------------------------
# Оценка маршрута
# ---------------------------------------------------------------------------
def evaluate_route(route: List[int], courier: Courier, scenario: Scenario,
                   time_scale: float = 1.0, start_time: float = 0.0) -> dict:
    """Моделирует выполнение маршрута одним курьером."""
    g = scenario.graph
    orders = {o.id: o for o in scenario.orders}
    t = start_time
    loc = courier.start
    load = 0.0
    max_load = 0.0
    delivered = []
    on_time = []
    late_minutes = 0.0
    reward = 0.0
    schedule = []
    feasible = True
    reason = ""

    for oid in route:
        o = orders[oid]
        travel1 = g.travel_time(loc, o.pickup) / courier.speed * time_scale
        t += travel1
        if t < o.ready:
            t = o.ready
        t += SERVICE_TIME
        load += o.weight
        max_load = max(max_load, load)
        if load > courier.capacity + 1e-9:
            feasible = False
            reason = "capacity"
            break
        travel2 = g.travel_time(o.pickup, o.delivery) / courier.speed * time_scale
        t += travel2
        t += SERVICE_TIME
        load -= o.weight
        if t > courier.shift_end + 1e-9:
            feasible = False
            reason = "shift_end"
            break
        delivered.append(oid)
        ot = t <= o.deadline + 1e-9
        on_time.append(ot)
        late_minutes += max(0.0, t - o.deadline)
        reward += o.reward if ot else 0.5 * o.reward
        schedule.append({"order": oid, "delivery_time": t,
                         "on_time": ot, "priority": o.priority})
        loc = o.delivery

    return {
        "feasible": feasible,
        "reason": reason,
        "completion": t,
        "cost": courier.cost_per_min * t,
        "reward": reward,
        "delivered": delivered,
        "on_time": on_time,
        "late_minutes": late_minutes,
        "schedule": schedule,
        "max_load": max_load,
        "travel_time": t - SERVICE_TIME * 2 * len(delivered),
    }


def best_insertion(courier: Courier, route: List[int], oid: int,
                   scenario: Scenario) -> dict:
    """Лучшая позиция вставки заказа в маршрут курьера."""
    best = None
    for pos in range(len(route) + 1):
        new_route = route[:pos] + [oid] + route[pos:]
        ev = evaluate_route(new_route, courier, scenario)
        if not ev["feasible"]:
            continue
        score = ev["completion"] + 0.35 * ev["cost"]
        if best is None or score < best["score"]:
            best = {"route": new_route, "score": score, "eval": ev}
    return best


# ---------------------------------------------------------------------------
# Метрики плана
# ---------------------------------------------------------------------------
def gini(values: List[float]) -> float:
    arr = np.array([max(0.0, v) for v in values], dtype=float)
    if arr.size == 0 or arr.sum() <= 1e-12:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * arr) / (n * arr.sum())) - (n + 1) / n)


def evaluate_plan(plan: Dict[int, List[int]], scenario: Scenario,
                  messages: int = 0, coordination_cost: float | None = None,
                  delay_scale: Dict[int, float] | None = None) -> dict:
    delay_scale = delay_scale or {}
    total_reward = total_cost = 0.0
    delivered, on_time, late = [], [], 0.0
    completions = []
    earnings = []
    delivery_times = []
    for c in scenario.couriers:
        route = plan.get(c.id, [])
        ev = evaluate_route(route, c, scenario, time_scale=delay_scale.get(c.id, 1.0))
        total_reward += ev["reward"]
        total_cost += ev["cost"]
        delivered.extend(ev["delivered"])
        on_time.extend(ev["on_time"])
        late += ev["late_minutes"]
        completions.append(ev["completion"] if route else 0.0)
        earnings.append(ev["reward"] - ev["cost"])
        delivery_times.extend(s["delivery_time"] for s in ev["schedule"])
    if coordination_cost is None:
        coordination_cost = messages * MSG_COST
    n_orders = len(scenario.orders)
    delivered_set = set(delivered)
    return {
        "delivered": len(delivered_set),
        "failed": n_orders - len(delivered_set),
        "on_time": int(sum(on_time)),
        "on_time_rate": float(sum(on_time) / n_orders) if n_orders else 0.0,
        "sla": float(sum(on_time) / n_orders) if n_orders else 0.0,
        "reward": float(total_reward),
        "transport_cost": float(total_cost),
        "coordination_cost": float(coordination_cost),
        "profit": float(total_reward - total_cost - coordination_cost),
        "makespan": float(max(completions) if completions else 0.0),
        "late_minutes": float(late),
        "messages": int(messages),
        "gini": gini(earnings),
        "utilization": float(np.mean([min(1.0, c / sc.shift_end)
                                      for c, sc in zip(completions, scenario.couriers)]))
        if scenario.couriers else 0.0,
        "avg_delivery_time": float(np.mean(delivery_times)) if delivery_times else 0.0,
    }
