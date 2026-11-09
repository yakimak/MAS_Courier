# -*- coding: utf-8 -*-
"""
Протоколы распределения заказов и координации в MAS-Courier.

Реализованы:
    * централизованная диспетчеризация;
    * контрактная сеть (CFP → PROPOSE → ACCEPT/REJECT);
    * аукцион (первая цена, закрытые ставки);
    * переговоры с чередующимися предложениями и арбитражем;
    * базовая FCFS-стратегия для сравнения «до/после».
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .model import (Courier, Scenario, best_insertion, evaluate_plan,
                    evaluate_route, MSG_COST)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _order_priority_key(o):
    return (-o.priority, o.deadline, -o.reward, o.id)


def _candidate_score(ins: dict, courier: Courier, route_len: int,
                     priority: int, reliability_weight: float = 12.0) -> float:
    return (ins["score"] + 3.0 * route_len - reliability_weight * courier.reliability
            - 6.0 * priority)


def _assign(plan: Dict[int, List[int]], cid: int, route: List[int]):
    plan[cid] = route


# ---------------------------------------------------------------------------
# Централизованная диспетчеризация
# ---------------------------------------------------------------------------
def centralized_dispatch(scenario: Scenario) -> dict:
    plan = {c.id: [] for c in scenario.couriers}
    messages = 0
    events = []
    for oid in sorted([o.id for o in scenario.orders],
                      key=lambda i: _order_priority_key(
                          next(o for o in scenario.orders if o.id == i))):
        best = None
        for c in scenario.couriers:
            ins = best_insertion(c, plan[c.id], oid, scenario)
            if ins is None:
                continue
            score = ins["score"]
            if best is None or score < best["score"]:
                best = {"cid": c.id, "route": ins["route"], "score": score}
        messages += 1
        if best is not None:
            _assign(plan, best["cid"], best["route"])
            messages += 1
            events.append({"order": oid, "courier": best["cid"],
                           "action": "ASSIGN", "protocol": "centralized"})
        else:
            events.append({"order": oid, "courier": None,
                           "action": "UNASSIGNED", "protocol": "centralized"})
    metrics = evaluate_plan(plan, scenario, messages=messages)
    return {"plan": plan, "metrics": metrics, "messages": messages,
            "events": events, "protocol": "centralized"}


# ---------------------------------------------------------------------------
# Контрактная сеть
# ---------------------------------------------------------------------------
def contract_net(scenario: Scenario) -> dict:
    plan = {c.id: [] for c in scenario.couriers}
    messages = 0
    events = []
    for oid in sorted([o.id for o in scenario.orders],
                      key=lambda i: _order_priority_key(
                          next(o for o in scenario.orders if o.id == i))):
        priority = next(o.priority for o in scenario.orders if o.id == oid)
        messages += 1  # CFP
        proposals = []
        for c in scenario.couriers:
            ins = best_insertion(c, plan[c.id], oid, scenario)
            if ins is None:
                continue
            messages += 1  # PROPOSE
            score = _candidate_score(ins, c, len(plan[c.id]), priority)
            proposals.append({"cid": c.id, "route": ins["route"],
                              "score": score, "ins": ins})
        if proposals:
            winner = min(proposals, key=lambda p: p["score"])
            _assign(plan, winner["cid"], winner["route"])
            messages += 1  # ACCEPT / AWARD
            events.append({"order": oid, "courier": winner["cid"],
                           "action": "AWARD", "bids": len(proposals),
                           "protocol": "contract_net"})
        else:
            messages += 1
            events.append({"order": oid, "courier": None,
                           "action": "NO_BIDS", "protocol": "contract_net"})
    metrics = evaluate_plan(plan, scenario, messages=messages)
    return {"plan": plan, "metrics": metrics, "messages": messages,
            "events": events, "protocol": "contract_net"}


# ---------------------------------------------------------------------------
# Аукцион
# ---------------------------------------------------------------------------
def auction(scenario: Scenario) -> dict:
    plan = {c.id: [] for c in scenario.couriers}
    messages = 0
    events = []
    for oid in sorted([o.id for o in scenario.orders],
                      key=lambda i: _order_priority_key(
                          next(o for o in scenario.orders if o.id == i))):
        priority = next(o.priority for o in scenario.orders if o.id == oid)
        messages += 1  # announcement
        bids = []
        rng = np.random.default_rng(scenario.seed * 1000 + oid)
        for c in scenario.couriers:
            ins = best_insertion(c, plan[c.id], oid, scenario)
            if ins is None:
                continue
            messages += 1  # bid
            # Ставка — цена с наценкой за загрузку и шум.
            bid = ins["eval"]["cost"] + 0.10 * ins["eval"]["completion"]
            bid *= 1.0 + 0.08 * len(plan[c.id])
            bid += rng.uniform(0.0, 8.0)
            bids.append({"cid": c.id, "route": ins["route"], "bid": bid})
        if bids:
            winner = min(bids, key=lambda b: b["bid"])
            _assign(plan, winner["cid"], winner["route"])
            messages += 1  # result
            events.append({"order": oid, "courier": winner["cid"],
                           "action": "WIN", "bids": len(bids),
                           "bid": winner["bid"], "protocol": "auction"})
        else:
            messages += 1
            events.append({"order": oid, "courier": None,
                           "action": "NO_BIDS", "protocol": "auction"})
    metrics = evaluate_plan(plan, scenario, messages=messages)
    return {"plan": plan, "metrics": metrics, "messages": messages,
            "events": events, "protocol": "auction"}


# ---------------------------------------------------------------------------
# FCFS — базовая стратегия «до» переговоров
# ---------------------------------------------------------------------------
def fcfs_dispatch(scenario: Scenario) -> dict:
    plan = {c.id: [] for c in scenario.couriers}
    messages = 0
    events = []
    for oid in sorted([o.id for o in scenario.orders]):
        messages += 1
        assigned = False
        for c in scenario.couriers:
            ins = best_insertion(c, plan[c.id], oid, scenario)
            if ins is not None:
                _assign(plan, c.id, ins["route"])
                messages += 1
                events.append({"order": oid, "courier": c.id,
                               "action": "ASSIGN_FCFS", "protocol": "fcfs"})
                assigned = True
                break
        if not assigned:
            events.append({"order": oid, "courier": None,
                           "action": "UNASSIGNED", "protocol": "fcfs"})
    metrics = evaluate_plan(plan, scenario, messages=messages)
    return {"plan": plan, "metrics": metrics, "messages": messages,
            "events": events, "protocol": "fcfs"}


# ---------------------------------------------------------------------------
# Переговоры
# ---------------------------------------------------------------------------
def negotiated_dispatch(scenario: Scenario, max_rounds: int = 3,
                        max_orders_per_courier: int = 4) -> dict:
    """
    Чередующиеся предложения:
        диспетчер предлагает компенсацию,
        курьер принимает или делает встречное предложение,
        после max_rounds — арбитраж по приоритету, надёжности и загрузке.
    """
    plan = {c.id: [] for c in scenario.couriers}
    messages = 0
    events = []
    rounds_total = 0

    for oid in sorted([o.id for o in scenario.orders],
                      key=lambda i: _order_priority_key(
                          next(o for o in scenario.orders if o.id == i))):
        order = next(o for o in scenario.orders if o.id == oid)
        candidates = []
        for c in scenario.couriers:
            if len(plan[c.id]) >= max_orders_per_courier:
                continue
            ins = best_insertion(c, plan[c.id], oid, scenario)
            if ins is None:
                continue
            candidates.append({"courier": c, "ins": ins})
        if not candidates:
            messages += 1
            events.append({"order": oid, "courier": None,
                           "action": "NO_CANDIDATES", "protocol": "negotiation"})
            continue

        compensation = 0.5 * order.reward
        accepted = []
        rounds = 0
        for rnd in range(max_rounds):
            rounds += 1
            messages += 1  # CFP / offer
            accepted = []
            for cand in candidates:
                c = cand["courier"]
                ev = cand["ins"]["eval"]
                # полезность курьера: компенсация минус затраты и риск опоздания
                late_risk = max(0.0, ev["completion"] - order.deadline) * 2.0
                utility = compensation - 0.55 * ev["cost"] - late_risk
                reservation = 8.0 + 2.0 * len(plan[c.id])
                messages += 1  # ответ
                if utility >= reservation:
                    accepted.append({**cand, "utility": utility})
                else:
                    need = (reservation + 0.55 * ev["cost"] + late_risk)
                    cand["counter"] = need
            if accepted:
                break
            # диспетчер повышает компенсацию
            compensation = min(order.reward, compensation * 1.35 + 5.0)
        rounds_total += rounds

        if accepted:
            # арбитраж: надёжность, загрузка, заявленная полезность
            winner = max(accepted, key=lambda a: (
                12.0 * a["courier"].reliability - 3.0 * len(plan[a["courier"].id])
                + 0.01 * a["utility"]))
            _assign(plan, winner["courier"].id, winner["ins"]["route"])
            messages += 1
            events.append({"order": oid, "courier": winner["courier"].id,
                           "action": "AGREEMENT", "rounds": rounds,
                           "compensation": compensation,
                           "protocol": "negotiation"})
        else:
            # арбитраж: выбрать лучшего по надёжности/времени, даже без согласия
            winner = min(candidates,
                         key=lambda a: (a["ins"]["score"]
                                        - 15.0 * a["courier"].reliability
                                        + 4.0 * len(plan[a["courier"].id])))
            _assign(plan, winner["courier"].id, winner["ins"]["route"])
            messages += 2
            events.append({"order": oid, "courier": winner["courier"].id,
                           "action": "ARBITRATION", "rounds": rounds,
                           "protocol": "negotiation"})

    metrics = evaluate_plan(plan, scenario, messages=messages)
    return {"plan": plan, "metrics": metrics, "messages": messages,
            "events": events, "protocol": "negotiation",
            "negotiation_rounds": rounds_total}


# ---------------------------------------------------------------------------
# Запуск по имени
# ---------------------------------------------------------------------------
def run_mechanism(name: str, scenario: Scenario) -> dict:
    if name == "centralized":
        return centralized_dispatch(scenario)
    if name == "contract_net":
        return contract_net(scenario)
    if name == "auction":
        return auction(scenario)
    if name == "fcfs":
        return fcfs_dispatch(scenario)
    if name == "negotiation":
        return negotiated_dispatch(scenario)
    raise ValueError(f"Неизвестный механизм: {name}")
