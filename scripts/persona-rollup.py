#!/usr/bin/env python3
"""
persona-rollup.py — recompute the per-persona board (portfolio/ai-team-data.json)
from curated BASELINES + LOGGED EVENTS. Companion to update-tracker.py (which owns
the category incident chart, ai-tracker-data.json). This owns the persona board.

WHY THIS EXISTS
  The board's tasksHandled / incidentsAttributed used to be hand-curated and went
  stale the moment the roster changed. This makes them computed and self-current —
  WITHOUT inventing anyone's numbers (the fleet-wide #4 rule).

DATA MODEL
  Each board persona carries baselineTasks / baselineIncidents — the curated
  2026-05-20 starting point. On first run these are seeded from the existing
  tasksHandled / incidentsAttributed so no history is lost. Live numbers are then:

      tasksHandled        = baselineTasks      + count(persona-tasks.jsonl for id)
      incidentsAttributed = baselineIncidents  + count(intake entries for id)

  Sources (both optional; missing = zero new):
      portfolio/persona-tasks.jsonl          {"date","persona","note"}   (one per task)
      portfolio/nightingale-intake.jsonl     {"date","cat","note","persona"}  (persona optional)
        + scripts/nightingale-archive/intake_*.jsonl   (archived incidents)

EARN-A-SLOT
  Personas on the BENCH (below) start at 0/0 and are NOT rendered. A benched
  persona is promoted onto the board only when its first task or incident is
  logged (live total > 0). New members therefore earn their slot by doing
  something — exactly the rule. Nobody gets fabricated numbers.

USAGE
  python persona-rollup.py            # recompute + write the board
  python persona-rollup.py --dry-run  # print what would change, write nothing

Stdlib only. ASCII output.
"""
import os
import sys
import json
import glob
import shutil
import argparse
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
BOARD = os.path.join(REPO, "portfolio", "ai-team-data.json")
TASKS_LOG = os.path.join(REPO, "portfolio", "persona-tasks.jsonl")
INTAKE = os.path.join(REPO, "portfolio", "nightingale-intake.jsonl")
ARCHIVE_GLOB = os.path.join(HERE, "nightingale-archive", "intake_*.jsonl")

# Roster members not yet profiled on the board. id/name/title/accent are factual
# roster data (assignable); tagline/description are left blank for Eris to curate
# when the persona earns its slot. Baselines are 0 — they prove themselves by working.
BENCH = [
    {"id": "aim",         "name": "AIM",          "title": "Asset Management",       "accent": "#6b7a4f"},
    {"id": "tiffany",     "name": "Tiffany & Co.", "title": "Analytics",             "accent": "#0abab5"},
    {"id": "marie-kondo", "name": "Marie Kondo",  "title": "Redundancy Auditor",     "accent": "#b8a9c9"},
    {"id": "lois-lane",   "name": "Lois Lane",    "title": "Outreach Director",      "accent": "#2c5f8a"},
    {"id": "mailchimp",   "name": "MailChimp",    "title": "Email Template Builder", "accent": "#e0b020"},
    {"id": "ouroboros",   "name": "Ouroboros",    "title": "Quality Engineer",       "accent": "#3a7d44"},
    {"id": "felix",       "name": "Fix-it Felix", "title": "Emergency Repair",       "accent": "#e8552d"},
    {"id": "hermes",      "name": "Hermes",       "title": "Email Compliance Officer", "accent": "#4a90d9"},
]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def load_jsonl(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def count_by_persona(entries):
    counts = {}
    for e in entries:
        pid = (e.get("persona") or "").strip().lower()
        if pid:
            counts[pid] = counts.get(pid, 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="Recompute the per-persona board from baselines + logged events.")
    ap.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    board = load_json(BOARD, None)
    if not board or "personas" not in board:
        sys.stderr.write("error: could not read %s\n" % BOARD)
        return 2

    personas = board["personas"]
    bench = board.get("bench", [])

    # 1. Seed baselines on first run (preserve the curated history; never lose it).
    for p in personas:
        p.setdefault("baselineTasks", int(p.get("tasksHandled", 0) or 0))
        p.setdefault("baselineIncidents", int(p.get("incidentsAttributed", 0) or 0))

    # 2. Make sure every BENCH member exists somewhere (board or bench), 0/0, uncurated.
    known = {p["id"] for p in personas} | {b["id"] for b in bench}
    for member in BENCH:
        if member["id"] not in known:
            bench.append({**member, "tagline": "", "description": "",
                          "baselineTasks": 0, "baselineIncidents": 0, "active": False})

    # 3. Tally logged events per persona.
    task_counts = count_by_persona(load_jsonl(TASKS_LOG))
    incident_entries = load_jsonl(INTAKE)
    for arc in glob.glob(ARCHIVE_GLOB):
        incident_entries += load_jsonl(arc)
    incident_counts = count_by_persona(incident_entries)

    def recompute(entry):
        bt = int(entry.get("baselineTasks", 0) or 0)
        bi = int(entry.get("baselineIncidents", 0) or 0)
        t = bt + task_counts.get(entry["id"], 0)
        i = bi + incident_counts.get(entry["id"], 0)
        entry["tasksHandled"] = t
        entry["incidentsAttributed"] = i
        entry["active"] = (t + i) > 0
        return t + i

    changes = []
    for p in personas:
        recompute(p)

    # 4. Promote benched personas that have earned a slot (logged activity > 0).
    still_benched = []
    for b in bench:
        total = recompute(b)
        if total > 0:
            personas.append(b)
            changes.append("PROMOTED %s (%s) -> board (%d tasks, %d incidents)"
                           % (b["id"], b.get("name", "?"), b["tasksHandled"], b["incidentsAttributed"]))
        else:
            still_benched.append(b)
    board["bench"] = still_benched

    board["lastUpdated"] = datetime.date.today().isoformat()
    board.setdefault("model",
        "Per-persona numbers = baseline (curated 2026-05-20) + logged events "
        "(persona-tasks.jsonl, nightingale-intake.jsonl). A benched persona joins "
        "the board on its first logged task/incident. Numbers are never invented; "
        "recompute with scripts/persona-rollup.py.")

    # Report
    print("=" * 64)
    print("PERSONA ROLLUP -- %s" % board["lastUpdated"])
    print("=" * 64)
    print("On board (earned): %d" % len(personas))
    for p in sorted(personas, key=lambda x: -(x["tasksHandled"] + x["incidentsAttributed"])):
        print("  %-14s %3d tasks  %3d incidents%s"
              % (p["id"], p["tasksHandled"], p["incidentsAttributed"],
                 "" if p.get("active") else "  (INACTIVE?)"))
    print("\nOn bench (no logged activity yet): %d" % len(still_benched))
    for b in still_benched:
        print("  %-14s %s" % (b["id"], b.get("name", "")))
    if changes:
        print("\nChanges this run:")
        for c in changes:
            print("  - " + c)
    print("=" * 64)

    if args.dry_run:
        print("DRY RUN — no file written.")
        return 0

    # Backup then write
    try:
        shutil.copy2(BOARD, BOARD + ".bak")
    except OSError:
        pass
    with open(BOARD, "w", encoding="utf-8") as fh:
        json.dump(board, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    # verify parseable
    try:
        load_json(BOARD, None)
    except Exception as e:
        sys.stderr.write("error: wrote invalid JSON: %s\n" % e)
        return 1
    print("Wrote %s" % BOARD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
