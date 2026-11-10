#!/usr/bin/env python3
"""Scarica i prezzi day-ahead da Energy-Charts (Fraunhofer ISE) e i prezzi domestici
da Eurostat, e aggiorna i file in data/. Pensato per GitHub Actions."""
import json, os, sys, time, datetime, urllib.request, urllib.error
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")
ZDIR = os.path.join(DATA, "zones")
TZ = ZoneInfo("Europe/Brussels")
ZONES = ["ES","PT","IT-North","IT-Centre-North","IT-Centre-South","IT-South","IT-Calabria","IT-Sicily","IT-Sardinia",
         "FR","DE-LU","AT","BE","NL","CH","PL","CZ","SK","HU","SI","HR","RO","BG","GR","RS","ME",
         "EE","LV","LT","FI","DK1","DK2","NO1","NO2","NO3","NO4","NO5","SE1","SE2","SE3","SE4"]
KEEP_DAYS = 800
EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204"
            "?format=JSON&lang=EN&nrg_cons=KWH2500-4999&tax=I_TAX&currency=EUR&unit=KWH&sinceTimePeriod=2024-S1")
UA = {"User-Agent": "borsa-elettrica/1.0 (github.com/valeriolo1983/borsa-elettrica)"}

def get_json(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = int(e.headers.get("Retry-After") or 0) or 8 * (k + 1)
                print(f"  {e.code}, attendo {wait}s", flush=True); time.sleep(wait); continue
            print(f"  HTTP {e.code} per {url}", flush=True); return None
        except Exception as e:
            print(f"  errore {e}, riprovo", flush=True); time.sleep(5 * (k + 1))
    return None

def summarize(j):
    """Media, minimo e massimo per giorno (ora CET) + profilo degli ultimi due giorni completi."""
    by = {}
    for t, p in zip(j.get("unix_seconds", []), j.get("price", [])):
        if p is None: continue
        dt = datetime.datetime.fromtimestamp(t, TZ)
        by.setdefault(dt.date().isoformat(), []).append((dt.hour * 60 + dt.minute, p))
    d, full_days = {}, {}
    for k, arr in by.items():
        arr.sort()
        step = max(1, arr[1][0] - arr[0][0]) if len(arr) > 1 else 60
        if len(arr) < round(1440 / step) * 0.9: continue
        v = [a[1] for a in arr]
        d[k] = [round(sum(v) / len(v), 2), round(min(v), 2), round(max(v), 2)]
        full_days[k] = (step, arr)
    q = {k: {"s": full_days[k][0], "v": [round(a[1], 2) for a in full_days[k][1]]} for k in sorted(d)[-2:]}
    return d, q

def write_zone(code, d):
    keys = sorted(d)[-KEEP_DAYS:]
    lines = ",\n".join(f'"{k}":{json.dumps(d[k])}' for k in keys)
    with open(os.path.join(ZDIR, code + ".json"), "w") as f:
        f.write('{"code":%s,"d":{\n%s\n}}\n' % (json.dumps(code), lines))

def write_status(failed):
    present = [z for z in ZONES if os.path.exists(os.path.join(ZDIR, z + ".json"))]
    with open(os.path.join(DATA, "status.json"), "w") as f:
        json.dump({"updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                   "zones": present, "failed": failed}, f)

def main():
    os.makedirs(ZDIR, exist_ok=True)
    today = datetime.datetime.now(TZ).date()
    end = (today + datetime.timedelta(days=2)).isoformat()
    prof_path = os.path.join(DATA, "profiles.json")
    profiles = json.load(open(prof_path)) if os.path.exists(prof_path) else {}
    ok, failed = [], []
    for code in ZONES:
        path = os.path.join(ZDIR, code + ".json")
        old = json.load(open(path))["d"] if os.path.exists(path) else {}
        start = (datetime.date.fromisoformat(max(old)) - datetime.timedelta(days=3)).isoformat() if old else \
                (today - datetime.timedelta(days=365)).isoformat()
        print(f"{code}: da {start}", flush=True)
        j = get_json(f"https://api.energy-charts.info/price?bzn={code}&start={start}&end={end}")
        if not j or not j.get("price"):
            failed.append(code); continue
        d, q = summarize(j)
        old.update(d); write_zone(code, old)
        if q: profiles[code] = q
        ok.append(code); write_status(failed)
        time.sleep(3)
    with open(prof_path, "w") as f:
        json.dump(profiles, f, separators=(",", ":"))
    e = get_json(EUROSTAT, tries=3)
    if e and "dimension" in e:
        geo, tim = e["dimension"]["geo"]["category"], e["dimension"]["time"]["category"]
        gi = sorted(geo["index"], key=geo["index"].get); ti = sorted(tim["index"], key=tim["index"].get)
        out = {}
        for a, g in enumerate(gi):
            row = {"name": geo["label"][g]}
            for b, t in enumerate(ti):
                v = e["value"].get(str(a * len(ti) + b))
                if v is not None: row[t] = v
            if len(row) > 1: out[g] = row
        with open(os.path.join(DATA, "eurostat.json"), "w") as f:
            json.dump({"updated": e.get("updated"), "times": ti, "data": out}, f, separators=(",", ":"))
    write_status(failed)
    print(f"aggiornate {len(ok)} zone, fallite: {failed}")
    if len(ok) == 0: sys.exit(1)

if __name__ == "__main__":
    main()
