# -*- coding: utf-8 -*-
"""
Диверсионный анализ MAS-Courier: инъекция неблагоприятных сценариев
и защитные механизмы.

Модель работает на уровне координации: faults меняют назначения,
задержки и сообщения, после чего план пересчитывается.
"""

from __future__ import annotations

import copy
from typing import Dict, List

import numpy as np

from .model import Scenario, best_insertion, evaluate_plan

FAULT_NAMES = {
    "fake_location": "Недостоверная геолокация",
    "goal_substitution": "Подмена цели агента",
    "map_outage": "Недоступность картографического сервиса",
    "wrong_delegation": "Некорректная передача полномочий",
    "circular_transfer": "Циклическая передача задачи",
    "contradictory": "Противоречивые указания",
}


def choose_faults(scenario: Scenario) -> List[str]:
    rng = np.random.default_rng(scenario.seed * 7919 + 13)
    faults = []
    if rng.random() < 0.55:
        faults.append("fake_location")
    if rng.random() < 0.45:
        faults.append("goal_substitution")
    if rng.random() < 0.40:
        faults.append("map_outage")
    if rng.random() < 0.35:
        faults.append("wrong_delegation")
    if rng.random() < 0.25:
        faults.append("circular_transfer")
    if rng.random() < 0.25:
        faults.append("contradictory")
    if not faults:
        faults.append("fake_location")
    return faults


def _reinsert(order_id: int, plan: Dict[int, List[int]], scenario: Scenario,
              exclude: int | None = None):
    best = None
    for c in scenario.couriers:
        if exclude is not None and c.id == exclude:
            continue
        ins = best_insertion(c, plan[c.id], order_id, scenario)
        if ins is None:
            continue
        score = ins["score"] + 3.0 * len(plan[c.id])
        if best is None or score < best["score"]:
            best = {"cid": c.id, "route": ins["route"], "score": score}
    if best is not None:
        plan[best["cid"]] = best["route"]
        return best["cid"]
    return None


def inject_faults(scenario: Scenario, base_result: dict,
                  defense: bool = False) -> dict:
    """
    Возвращает метрики после инъекции fault'ов.
    defense=False — система без защитных механизмов;
    defense=True  — с валидацией, мониторингом, токенами владения и fallback.
    """
    plan = {cid: list(route) for cid, route in base_result["plan"].items()}
    messages = int(base_result["messages"])
    base_messages = messages
    delay_scale: Dict[int, float] = {}
    removed: set[int] = set()
    fault_events = []
    detection_times = []
    faults = choose_faults(scenario)
    rng = np.random.default_rng(scenario.seed * 104729 + (1 if defense else 0))

    for fault in faults:
        event = {"fault": fault, "name": FAULT_NAMES[fault],
                 "defense": defense, "detected": False,
                 "detection_time": None, "action": ""}
        if fault == "fake_location":
            affected = rng.choice([c.id for c in scenario.couriers],
                                  size=min(2, len(scenario.couriers)), replace=False)
            if defense:
                for cid in affected:
                    delay_scale[cid] = max(delay_scale.get(cid, 1.0), 1.03)
                messages += 2 * len(affected)
                detection_times.append(4.0)
                event.update(detected=True, detection_time=4.0,
                             action="сверка геолокации и ETA, корректировка")
            else:
                for cid in affected:
                    delay_scale[cid] = max(delay_scale.get(cid, 1.0), 1.18)
                event["action"] = "неверный ETA, опоздания"

        elif fault == "goal_substitution":
            candidates = [cid for cid, r in plan.items() if r]
            if candidates:
                cid = int(rng.choice(candidates))
                oid = plan[cid][0]
                plan[cid] = plan[cid][1:]
                if defense:
                    new_cid = _reinsert(oid, plan, scenario, exclude=cid)
                    messages += 4
                    detection_times.append(8.0)
                    if new_cid is not None:
                        event.update(detected=True, detection_time=8.0,
                                     action=f"обнаружено, заказ передан курьеру {new_cid}")
                    else:
                        removed.add(oid)
                        event.update(detected=True, detection_time=8.0,
                                     action="обнаружено, переназначить не удалось")
                else:
                    removed.add(oid)
                    event["action"] = "заказ потерян"

        elif fault == "map_outage":
            if defense:
                for c in scenario.couriers:
                    delay_scale[c.id] = max(delay_scale.get(c.id, 1.0), 1.05)
                messages += len(scenario.couriers)
                detection_times.append(1.0)
                event.update(detected=True, detection_time=1.0,
                             action="fallback на кэшированный граф")
            else:
                for c in scenario.couriers:
                    delay_scale[c.id] = max(delay_scale.get(c.id, 1.0), 1.22)
                event["action"] = "маршруты по устаревшему графу"

        elif fault == "wrong_delegation":
            candidates = [cid for cid, r in plan.items() if r]
            if candidates:
                cid = int(rng.choice(candidates))
                oid = plan[cid][0]
                if defense:
                    messages += 2
                    detection_times.append(1.0)
                    event.update(detected=True, detection_time=1.0,
                                 action="валидация состояния курьера, назначение отклонено")
                else:
                    plan[cid] = plan[cid][1:]
                    removed.add(oid)
                    event["action"] = "назначение не выполнено"

        elif fault == "circular_transfer":
            all_orders = [oid for r in plan.values() for oid in r]
            if all_orders:
                oid = int(rng.choice(all_orders))
                if defense:
                    messages += 1
                    detection_times.append(1.0)
                    event.update(detected=True, detection_time=1.0,
                                 action="токен владения с TTL предотвратил цикл")
                else:
                    for cid in plan:
                        if oid in plan[cid]:
                            plan[cid].remove(oid)
                            break
                    removed.add(oid)
                    event["action"] = "цикл A→B→A, заказ потерян"

        elif fault == "contradictory":
            all_orders = [oid for r in plan.values() for oid in r]
            if all_orders:
                oid = int(rng.choice(all_orders))
                if defense:
                    messages += 2
                    detection_times.append(1.0)
                    event.update(detected=True, detection_time=1.0,
                                 action="версионирование и блокировка владельца")
                else:
                    for cid in plan:
                        if oid in plan[cid]:
                            plan[cid].remove(oid)
                            break
                    removed.add(oid)
                    event["action"] = "дублирующее указание, заказ потерян"

        fault_events.append(event)

    metrics = evaluate_plan(plan, scenario, messages=messages,
                            delay_scale=delay_scale)
    metrics["faults"] = [f["fault"] for f in fault_events]
    metrics["detected"] = sum(1 for f in fault_events if f["detected"])
    metrics["detection_time"] = (float(np.mean(detection_times))
                                 if detection_times else 0.0)
    metrics["overhead_messages"] = messages - base_messages
    metrics["false_positive_rate"] = 0.01 if defense else 0.0
    return {"plan": plan, "metrics": metrics, "events": fault_events,
            "faults": faults, "removed": sorted(removed)}
