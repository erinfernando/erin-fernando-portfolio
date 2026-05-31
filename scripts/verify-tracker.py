"""
Nightingale Tracker Verification
Runs at 12:15 AM. Checks that the midnight update succeeded.

Sequence:
  1. Read nightingale-status.json from the midnight run
  2. If status is OK — done, log and exit
  3. If status is FAIL/PARTIAL/missing — retry update-tracker.py
  4. If retry succeeds — done, log recovery
  5. If retry fails — ALERT: create GitHub issue + write error flag

The GitHub issue triggers an email notification. The error flag is read
by Nightingale at session start, who routes it to Donna as a to-do.
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime

REPO_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.dirname(__file__)
STATUS_FILE = os.path.join(SCRIPTS_DIR, "nightingale-status.json")
ERROR_FLAG = os.path.join(SCRIPTS_DIR, "nightingale-error.json")
LOG_FILE = os.path.join(SCRIPTS_DIR, "update-tracker.log")
TRACKER_JSON = os.path.join(REPO_DIR, "portfolio", "ai-tracker-data.json")
PYTHON = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Programs", "Python", "Python314", "python.exe"
)
UPDATE_SCRIPT = os.path.join(SCRIPTS_DIR, "update-tracker.py")


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [verify] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_status():
    """Read the status file left by update-tracker.py."""
    if not os.path.exists(STATUS_FILE):
        return None
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def check_tracker_current():
    """Verify the tracker JSON has today's date."""
    try:
        with open(TRACKER_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        today = date.today().isoformat()
        return today in data.get("dates", [])
    except Exception:
        return False


def check_git_pushed():
    """Check if local is ahead of remote (unpushed commits)."""
    git = ["git", "-C", REPO_DIR]
    try:
        subprocess.run(
            git + ["fetch", "--quiet"],
            capture_output=True, timeout=30
        )
        result = subprocess.run(
            git + ["rev-list", "--count", "HEAD...@{u}"],
            capture_output=True, text=True, timeout=10
        )
        ahead = int(result.stdout.strip())
        return ahead == 0
    except Exception:
        return False  # can't verify = treat as failure


def retry_update():
    """Re-run update-tracker.py. Returns True on success."""
    log("Retrying update-tracker.py...")
    try:
        result = subprocess.run(
            [PYTHON, UPDATE_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log("Retry succeeded")
            return True
        else:
            log(f"Retry failed (exit {result.returncode}): {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log("Retry timed out after 120s")
        return False
    except Exception as e:
        log(f"Retry error: {e}")
        return False


def create_github_issue(error_detail):
    """Create a GitHub issue for the failed update. Generates email notification."""
    today = date.today().isoformat()
    title = f"Nightingale: tracker update failed ({today})"
    body = (
        f"## Automated alert\n\n"
        f"The Nightingale tracker auto-update failed twice on **{today}**.\n\n"
        f"**Error:** {error_detail}\n\n"
        f"### What to check\n"
        f"- [ ] Is the repo in a clean state? (`git status`)\n"
        f"- [ ] Can you push manually? (`git push`)\n"
        f"- [ ] Is `ai-tracker-data.json` valid JSON?\n"
        f"- [ ] Check `scripts/update-tracker.log` for details\n\n"
        f"This issue was created automatically by `verify-tracker.py`."
    )
    try:
        result = subprocess.run(
            [r"C:\Program Files\GitHub CLI\gh.exe", "issue", "create",
             "--repo", "erinfernando/erin-fernando-portfolio",
             "--title", title,
             "--body", body,
             "--label", "bug"],
            capture_output=True, text=True, timeout=30,
            cwd=REPO_DIR
        )
        if result.returncode == 0:
            log(f"GitHub issue created: {result.stdout.strip()}")
            return True
        else:
            log(f"GitHub issue creation failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"Could not create GitHub issue: {e}")
        return False


def write_error_flag(error_detail):
    """Write error flag for Nightingale to read at session start."""
    data = {
        "error": True,
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "detail": error_detail,
        "action_required": "Route to Donna: tracker auto-update failed twice. "
                           "Check scripts/update-tracker.log and resolve manually.",
        "retries_exhausted": True
    }
    try:
        with open(ERROR_FLAG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        log(f"Error flag written to {os.path.basename(ERROR_FLAG)}")
    except OSError as e:
        log(f"Could not write error flag: {e}")


def clear_error_flag():
    """Remove error flag if a previous failure has been resolved."""
    if os.path.exists(ERROR_FLAG):
        try:
            os.remove(ERROR_FLAG)
            log("Previous error flag cleared")
        except OSError:
            pass


def main():
    log("--- Verification started ---")
    today = date.today().isoformat()

    # Step 1: Check status from midnight run
    status = read_status()

    if status and status.get("date") == today and status.get("status") == "OK":
        # Midnight run reported success — verify it's true
        tracker_ok = check_tracker_current()
        push_ok = check_git_pushed()

        if tracker_ok and push_ok:
            log("Verification passed: tracker current, push confirmed")
            clear_error_flag()
            return 0
        elif tracker_ok and not push_ok:
            log("Tracker updated but push unconfirmed — attempting push only")
            git = ["git", "-C", REPO_DIR]
            try:
                subprocess.run(git + ["push"], check=True, capture_output=True, timeout=30)
                log("Push recovered")
                clear_error_flag()
                return 0
            except Exception:
                log("Push recovery failed — will retry full update")
        else:
            log(f"Status says OK but tracker missing today. tracker_ok={tracker_ok}")

    elif status and status.get("date") == today:
        log(f"Midnight run status: {status.get('status')} — {status.get('detail', '')}")
    else:
        log("No status file for today — midnight run may not have fired")

    # Step 2: First retry
    if retry_update():
        # Verify the retry actually worked
        new_status = read_status()
        if new_status and new_status.get("status") == "OK":
            log("Recovery successful after retry")
            clear_error_flag()
            return 0
        else:
            log("Retry ran but status is not OK")

    # Step 3: Retry failed — escalate
    error_detail = "Unknown"
    status = read_status()
    if status:
        error_detail = status.get("detail", "No detail")

    log(f"DOUBLE FAILURE — escalating. Error: {error_detail}")
    write_error_flag(error_detail)
    create_github_issue(error_detail)

    log("--- Verification failed: alert sent ---")
    return 1


if __name__ == "__main__":
    sys.exit(main())
