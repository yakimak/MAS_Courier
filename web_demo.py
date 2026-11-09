# -*- coding: utf-8 -*-
"""
Веб-демонстрация MAS-Courier на стандартной библиотеке Python.
Запуск:
    python web_demo.py
Открыть: http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mas import generate_scenario, run_mechanism
from mas.faults import inject_faults

HTML = r"""
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>MAS-Courier · демонстрация</title>
<style>
  :root { --bg:#f5f7fa; --card:#ffffff; --ink:#12263a; --accent:#2f5d8a; --ok:#27ae60; --bad:#c0392b; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", system-ui, sans-serif; background:var(--bg); color:var(--ink); }
  header { background:linear-gradient(135deg,#12263a,#2f5d8a); color:white; padding:22px 28px; }
  header h1 { margin:0 0 4px; font-size:24px; }
  header p { margin:0; opacity:.85; }
  main { max-width:1200px; margin:22px auto; padding:0 18px; display:grid; gap:18px; }
  .card { background:var(--card); border-radius:14px; padding:18px 20px; box-shadow:0 4px 18px rgba(18,38,58,.08); }
  .controls { display:grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap:12px; align-items:end; }
  label { display:flex; flex-direction:column; font-size:12px; font-weight:600; color:#566573; gap:5px; }
  select, input { padding:8px 10px; border:1px solid #cfd8e3; border-radius:8px; font-size:14px; background:white; }
  button { grid-column:1/-1; padding:12px; border:0; border-radius:10px; background:var(--accent); color:white; font-size:15px; font-weight:700; cursor:pointer; }
  button:hover { background:#244a70; }
  .metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; }
  .metric { background:#eef4fb; border-radius:10px; padding:12px; }
  .metric .v { font-size:22px; font-weight:800; color:var(--accent); }
  .metric .k { font-size:11px; color:#566573; text-transform:uppercase; letter-spacing:.04em; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { padding:7px 8px; border-bottom:1px solid #e5eaf0; text-align:left; }
  th { color:#566573; font-size:11px; text-transform:uppercase; }
  .ok { color:var(--ok); font-weight:700; }
  .bad { color:var(--bad); font-weight:700; }
  .log { font-family: Consolas, monospace; font-size:12px; max-height:260px; overflow:auto; background:#0f1b2a; color:#d6e4f0; padding:12px; border-radius:10px; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
  @media (max-width:800px){ .row{grid-template-columns:1fr;} }
</style>
</head>
<body>
<header>
  <h1>MAS-Courier</h1>
  <p>Многоагентная система курьерской доставки · интерактивная демонстрация</p>
</header>
<main>
  <section class="card">
    <div class="controls">
      <label>Механизм
        <select id="mechanism">
          <option value="contract_net">Контрактная сеть</option>
          <option value="centralized">Централизованный</option>
          <option value="auction">Аукцион</option>
          <option value="fcfs">FCFS (до переговоров)</option>
          <option value="negotiation">Переговоры</option>
        </select>
      </label>
      <label>Seed <input id="seed" type="number" value="42"></label>
      <label>Заказов <input id="orders" type="number" value="15"></label>
      <label>Курьеров <input id="couriers" type="number" value="5"></label>
      <label>Fault-режим
        <select id="faults">
          <option value="none">без fault'ов</option>
          <option value="baseline">fault'ы без защиты</option>
          <option value="defended">fault'ы с защитой</option>
        </select>
      </label>
      <button onclick="run()">Запустить симуляцию</button>
    </div>
  </section>

  <section class="card">
    <h2 style="margin-top:0">Метрики</h2>
    <div id="metrics" class="metrics"></div>
  </section>

  <div class="row">
    <section class="card">
      <h2 style="margin-top:0">План</h2>
      <table id="plan"><thead><tr><th>Курьер</th><th>Заказы</th></tr></thead><tbody></tbody></table>
    </section>
    <section class="card">
      <h2 style="margin-top:0">Журнал</h2>
      <div id="log" class="log">Нажмите «Запустить симуляцию».</div>
    </section>
  </div>
</main>
<script>
const fmt = (v, d=2) => (typeof v === 'number' ? v.toFixed(d) : v);
async function run() {
  const payload = {
    mechanism: document.getElementById('mechanism').value,
    seed: +document.getElementById('seed').value,
    orders: +document.getElementById('orders').value,
    couriers: +document.getElementById('couriers').value,
    fault_mode: document.getElementById('faults').value
  };
  const res = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const data = await res.json();
  const m = data.metrics;
  const items = [
    ['Прибыль', fmt(m.profit,1)],
    ['SLA', fmt(m.on_time_rate,3)],
    ['Доставлено', `${m.delivered} / ${m.delivered + m.failed}`],
    ['Сообщений', m.messages],
    ['Gini', fmt(m.gini,3)],
    ['Makespan', fmt(m.makespan,1)],
    ['Накладные', m.overhead_messages ?? 0],
    ['Обнаружено', m.detected ?? '—']
  ];
  document.getElementById('metrics').innerHTML = items.map(([k,v]) =>
    `<div class="metric"><div class="v">${v}</div><div class="k">${k}</div></div>`).join('');
  const tbody = document.querySelector('#plan tbody');
  tbody.innerHTML = '';
  for (const c of data.couriers) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${c.id}</td><td>${(c.orders||[]).join(', ') || '—'}</td>`;
    tbody.appendChild(tr);
  }
  document.getElementById('log').textContent = data.log.join('\n');
}
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML, "text/html")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/run":
            self._send(404, "not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            mechanism = payload.get("mechanism", "contract_net")
            seed = int(payload.get("seed", 42))
            orders = int(payload.get("orders", 15))
            couriers = int(payload.get("couriers", 5))
            fault_mode = payload.get("fault_mode", "none")

            scenario = generate_scenario(seed, orders, couriers, name=mechanism)
            result = run_mechanism(mechanism, scenario)
            metrics = result["metrics"]
            events = result.get("events", [])

            if fault_mode in ("baseline", "defended"):
                base = run_mechanism("contract_net", scenario)
                fault_res = inject_faults(scenario, base, defense=(fault_mode == "defended"))
                metrics = fault_res["metrics"]
                events = fault_res["events"]

            log = []
            for e in events[:40]:
                if "fault" in e:
                    log.append(f"[fault] {e.get('name', e.get('fault'))}: {e.get('action')}")
                else:
                    log.append(f"[{e.get('protocol','')}] order={e.get('order')} "
                               f"courier={e.get('courier')} action={e.get('action')}")
            log.append("")
            log.append("План: " + ", ".join(
                f"курьер {c.id}: {result['plan'].get(c.id, [])}" for c in scenario.couriers))

            body = {
                "metrics": metrics,
                "couriers": [{"id": c.id, "orders": result["plan"].get(c.id, [])}
                             for c in scenario.couriers],
                "log": log,
            }
            self._send(200, json.dumps(body, ensure_ascii=False, default=float))
        except Exception as exc:
            self._send(500, json.dumps({"error": str(exc)}, ensure_ascii=False))

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"MAS-Courier web demo: http://localhost:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
