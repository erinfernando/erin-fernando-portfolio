# Per-Persona Board Tracking

How the team board (`portfolio/ai-team-data.json`) stays current **without anyone
inventing numbers**. Companion to the category incident chart (`ai-tracker-data.json`,
owned by `update-tracker.py`).

## The model: baseline + logged events
Each persona's live numbers are computed, not hand-set:

```
tasksHandled        = baselineTasks      + (logged tasks for this persona)
incidentsAttributed = baselineIncidents  + (logged incidents for this persona)
```

- **baselines** = the curated 2026-05-20 starting point, seeded once and preserved so
  no history is lost.
- **logged events** accrue going forward from the two logs below.
- A persona with no baseline and no logged events stays at **0** — never a guess.

## Earn-a-slot
New roster members live on the **bench** (`ai-team-data.json` → `bench[]`) at 0/0 and
do **not** render. The first time a benched persona logs a task or incident,
`persona-rollup.py` **promotes** it onto the board. Members earn their slot by working.
(Hermes and Fix-it Felix are benched right now — zero logged activity.)

## How to log (the part that makes it live)

**Tasks** → append one line per task handled to `portfolio/persona-tasks.jsonl`:
```json
{"date": "2026-05-30", "persona": "hermes", "note": "scriptingwitch.com email posture audit"}
```
Owner: **Donna** logs a line when she closes/credits a task to a specialist.

**Incidents** → the existing Nightingale intake (`portfolio/nightingale-intake.jsonl`)
gains an **optional** `persona` field (the skill id):
```json
{"date": "2026-05-30", "cat": 8, "note": "...", "persona": "craig"}
```
Owner: **Nightingale** adds `persona` when an incident is attributable to one skill.
(Entries without `persona` still count toward the category chart — backward compatible.)

`persona` is the skill **id** (lowercase): `donna, harvey, craig, lovelace, dior, page,
john-wick, hackerman, leslie-knope, nightingale, theseus, aim, tiffany, marie-kondo,
lois-lane, mailchimp, ouroboros, felix, hermes`.

## Recompute
```
python scripts/persona-rollup.py            # recompute + write the board
python scripts/persona-rollup.py --dry-run  # preview, write nothing
```
Writes a `.bak`, validates JSON, bumps `lastUpdated`. Safe to run any time.

## To make it fully automatic (TODO)
Add `persona-rollup.py` to the midnight run next to `update-tracker.py` (so the board
refreshes nightly). Until then it's on-demand — run it after a session with logged
activity. Wiring the scheduled task is a config change (Eris's call).

## Curating a newly-promoted persona
When a benched persona is promoted, its `tagline`/`description` are blank (id/name/title/
accent are pre-filled). Eris writes the in-character tagline/description — the numbers are
automated, the *voice* stays curated.
