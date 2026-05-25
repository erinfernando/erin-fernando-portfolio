"""
Nightingale Tracker Auto-Update
Runs at midnight. Processes the intake log, updates ai-tracker-data.json,
commits, and pushes to GitHub so the live site reflects the latest data.

Intake format (nightingale-intake.jsonl) — one JSON object per line:
  {"date": "2026-05-22", "cat": 8, "note": "Silent failure in CSS review"}

If no intake entries exist, the script still adds today's date to the chart
with carried-forward values (shows zero new issues, which is valid data).

Safety features:
  - Lock file prevents concurrent runs
  - Backup created before any modification
  - JSON validation after save (structure, array lengths, non-decreasing)
  - Git state check before committing
  - Status file written for verify-tracker.py and Nightingale to read
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from collections import defaultdict

REPO_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TRACKER_JSON = os.path.join(REPO_DIR, "portfolio", "ai-tracker-data.json")
INTAKE_FILE = os.path.join(REPO_DIR, "portfolio", "nightingale-intake.jsonl")
ARCHIVE_DIR = os.path.join(REPO_DIR, "scripts", "nightingale-archive")
BACKUP_DIR = os.path.join(REPO_DIR, "scripts", "nightingale-backups")
LOG_FILE = os.path.join(REPO_DIR, "scripts", "update-tracker.log")
LOCK_FILE = os.path.join(REPO_DIR, "scripts", ".tracker-update.lock")
STATUS_FILE = os.path.join(REPO_DIR, "scripts", "nightingale-status.json")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Lock file — prevent concurrent runs
# ---------------------------------------------------------------------------

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                lock_data = json.load(f)
            lock_age = time.time() - lock_data.get("timestamp", 0)
            if lock_age < 600:  # 10 minutes — still fresh
                log(f"Lock held by PID {lock_data.get('pid')} ({lock_age:.0f}s ago). Aborting.")
                return False
            else:
                log(f"Stale lock ({lock_age:.0f}s old). Overriding.")
        except (json.JSONDecodeError, OSError):
            log("Corrupt lock file. Overriding.")
    with open(LOCK_FILE, "w") as f:
        json.dump({"pid": os.getpid(), "timestamp": time.time()}, f)
    return True


def release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Status file — read by verify-tracker.py and Nightingale
# ---------------------------------------------------------------------------

def write_status(status, detail=""):
    data = {
        "last_run": datetime.now().isoformat(),
        "status": status,
        "detail": detail,
        "date": date.today().isoformat()
    }
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        log(f"Could not write status file: {e}")


# ---------------------------------------------------------------------------
# Backup and restore
# ---------------------------------------------------------------------------

def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = date.today().isoformat()
    backup_path = os.path.join(BACKUP_DIR, f"tracker_{today}.json")
    shutil.copy2(TRACKER_JSON, backup_path)
    log(f"Backup created: {os.path.basename(backup_path)}")
    # Keep only the last 7 backups
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("tracker_")],
        reverse=True
    )
    for old in backups[7:]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return backup_path


def restore_backup(backup_path):
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, TRACKER_JSON)
        log(f"Restored from backup: {os.path.basename(backup_path)}")
        return True
    log("No backup to restore from")
    return False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_tracker():
    with open(TRACKER_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tracker(data):
    with open(TRACKER_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_intake():
    entries = []
    if not os.path.exists(INTAKE_FILE):
        return entries
    with open(INTAKE_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                log(f"Skipping malformed intake line {i}: {line[:80]}")
    return entries


def archive_intake():
    if not os.path.exists(INTAKE_FILE):
        return
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    today = date.today().isoformat()
    archive_path = os.path.join(ARCHIVE_DIR, f"intake_{today}.jsonl")
    if os.path.exists(archive_path):
        with open(INTAKE_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(archive_path, "a", encoding="utf-8") as dst:
            dst.write(content)
        os.remove(INTAKE_FILE)
    else:
        os.rename(INTAKE_FILE, archive_path)
    log(f"Archived intake to {os.path.basename(archive_path)}")


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------

def validate_tracker(data):
    """Check structural integrity of tracker data. Returns (ok, errors)."""
    errors = []

    if "dates" not in data or "categories" not in data:
        errors.append("Missing 'dates' or 'categories' key")
        return False, errors

    n_dates = len(data["dates"])
    if n_dates == 0:
        errors.append("Dates array is empty")
        return False, errors

    for cat_id, cat in data["categories"].items():
        if "data" not in cat or "baseline" not in cat:
            errors.append(f"Category {cat_id}: missing 'data' or 'baseline'")
            continue

        if len(cat["data"]) != n_dates:
            errors.append(
                f"Category {cat_id}: data length {len(cat['data'])} != dates length {n_dates}"
            )

        if len(cat["baseline"]) != n_dates:
            errors.append(
                f"Category {cat_id}: baseline length {len(cat['baseline'])} != dates length {n_dates}"
            )

        # Cumulative values should never decrease
        for i in range(1, len(cat["data"])):
            if cat["data"][i] < cat["data"][i - 1]:
                errors.append(
                    f"Category {cat_id}: data decreased at index {i} "
                    f"({cat['data'][i - 1]} -> {cat['data'][i]})"
                )
                break  # one per category is enough

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------

def ensure_today(tracker):
    """Add today's date column if missing. Carry forward last values."""
    today = date.today().isoformat()
    if today in tracker["dates"]:
        return False
    tracker["dates"].append(today)
    for cat_data in tracker["categories"].values():
        last_val = cat_data["data"][-1] if cat_data["data"] else 0
        cat_data["data"].append(last_val)
        last_base = cat_data["baseline"][-1] if cat_data["baseline"] else 0
        cat_data["baseline"].append(last_base)
    return True


def apply_intake(tracker, entries):
    """Add intake entries to today's cumulative totals."""
    if not entries:
        return 0
    new_counts = defaultdict(int)
    for entry in entries:
        cat = str(entry.get("cat", ""))
        if cat in tracker["categories"]:
            new_counts[cat] += 1
        else:
            log(f"Unknown category {cat}, skipping: {entry.get('note', '')[:60]}")
    for cat_id, count in new_counts.items():
        tracker["categories"][cat_id]["data"][-1] += count
    return sum(new_counts.values())


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

def check_git_state():
    """Verify repo is in a safe state for auto-commit."""
    git = ["git", "-C", REPO_DIR]
    try:
        # Check not in a merge/rebase
        result = subprocess.run(
            git + ["rev-parse", "--git-dir"],
            capture_output=True, text=True
        )
        git_dir = os.path.join(REPO_DIR, result.stdout.strip())
        for danger_file in ["MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD"]:
            if os.path.exists(os.path.join(git_dir, danger_file)):
                log(f"Git repo is mid-{danger_file.split('_')[0].lower()}. Skipping commit.")
                return False

        # Check not detached HEAD
        result = subprocess.run(
            git + ["symbolic-ref", "--quiet", "HEAD"],
            capture_output=True
        )
        if result.returncode != 0:
            log("Detached HEAD state. Skipping commit.")
            return False

        return True
    except Exception as e:
        log(f"Git state check failed: {e}")
        return False


def git_commit_push():
    """Stage, commit, and push. Returns True on success."""
    if not check_git_state():
        return False

    git = ["git", "-C", REPO_DIR]
    try:
        subprocess.run(
            git + ["add", "portfolio/ai-tracker-data.json"],
            check=True, capture_output=True
        )
        result = subprocess.run(
            git + ["diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode == 0:
            log("No changes to commit")
            return True
        subprocess.run(
            git + ["commit", "-m", "Nightingale: daily tracker update"],
            check=True, capture_output=True
        )
        subprocess.run(
            git + ["push"],
            check=True, capture_output=True
        )
        log("Committed and pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Git error: {e.stderr.decode('utf-8', errors='replace')[:200]}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("--- Nightingale auto-update started ---")

    if not acquire_lock():
        write_status("SKIPPED", "Lock held by another process")
        return 1

    try:
        # Backup before touching anything
        backup_path = create_backup()

        tracker = load_tracker()
        entries = load_intake()

        added_day = ensure_today(tracker)
        count = apply_intake(tracker, entries)

        if added_day or count > 0:
            tracker["lastUpdated"] = date.today().isoformat()
            save_tracker(tracker)

            # Validate after save
            ok, errors = validate_tracker(tracker)
            if not ok:
                log(f"VALIDATION FAILED: {errors}")
                restore_backup(backup_path)
                write_status("FAIL", f"Validation errors: {'; '.join(errors)}")
                return 1

            # Re-read and verify JSON is parseable
            try:
                with open(TRACKER_JSON, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                log(f"CORRUPT JSON after save: {e}")
                restore_backup(backup_path)
                write_status("FAIL", f"Corrupt JSON: {e}")
                return 1

            log(f"Updated tracker: +{count} issues, new day={added_day}")
            if entries:
                archive_intake()

            pushed = git_commit_push()
            if pushed:
                write_status("OK", f"+{count} issues, pushed")
            else:
                write_status("PARTIAL", f"+{count} issues, JSON updated but push failed")
                return 1
        else:
            log("No updates needed")
            write_status("OK", "No updates needed")

        log("--- Done ---")
        return 0

    except Exception as e:
        log(f"UNEXPECTED ERROR: {e}")
        write_status("FAIL", str(e))
        return 1

    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
