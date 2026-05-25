# Nightingale Automation Setup

Prerequisites and configuration required for the automated tracker pipeline.

## Scheduled Tasks

Two Windows scheduled tasks must be registered and enabled:

| Task | Time | Script |
|------|------|--------|
| Nightingale Tracker Update | 12:00 AM | `update-tracker.py` |
| Nightingale Tracker Verify | 12:15 AM | `verify-tracker.py` |

To check they exist:
```powershell
Get-ScheduledTask -TaskName "Nightingale*"
```

To re-register if missing:
```powershell
# Midnight update
$action = New-ScheduledTaskAction -Execute "C:\Users\panic\AppData\Local\Programs\Python\Python314\python.exe" -Argument "C:\Users\panic\Downloads\erin-portfolio\scripts\update-tracker.py" -WorkingDirectory "C:\Users\panic\Downloads\erin-portfolio"
$trigger = New-ScheduledTaskTrigger -Daily -At "12:00AM"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "Nightingale Tracker Update" -Action $action -Trigger $trigger -Settings $settings -Force

# 12:15 verification
$action = New-ScheduledTaskAction -Execute "C:\Users\panic\AppData\Local\Programs\Python\Python314\python.exe" -Argument "C:\Users\panic\Downloads\erin-portfolio\scripts\verify-tracker.py" -WorkingDirectory "C:\Users\panic\Downloads\erin-portfolio"
$trigger = New-ScheduledTaskTrigger -Daily -At "12:15AM"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "Nightingale Tracker Verify" -Action $action -Trigger $trigger -Settings $settings -Force
```

## GitHub Notification Settings

The double-failure alert creates a GitHub issue, which triggers an email
via GitHub's notification system. These settings must be enabled:

1. **GitHub.com > Settings > Notifications**
   - Default notifications email: set to your active email
   - Email notification preferences: **Issues** must be checked

2. **Repository watch setting**
   - Go to `github.com/erinfernando/erin-fernando-portfolio`
   - Click **Watch** dropdown > select **All Activity** (or at minimum "Custom" with Issues checked)

3. **GitHub CLI authentication**
   - The `gh` CLI must be logged in for issue creation to work
   - Check: `gh auth status`
   - If not authenticated: `gh auth login`

## Git Credentials

The midnight script runs `git push` without interactive input.
Git must have stored credentials (HTTPS) or an SSH key configured.

- Check: `git -C "C:\Users\panic\Downloads\erin-portfolio" push --dry-run`
- If prompted for password, configure credential storage:
  ```
  git config --global credential.helper manager
  ```
  Then do one manual push to store the credential.

## GitHub Issue Label

The verification script creates issues with `--label bug`.
This label must exist on the repository.

- Check: `gh label list --repo erinfernando/erin-fernando-portfolio`
- If missing: `gh label create bug --description "Something isn't working" --color d73a4a --repo erinfernando/erin-fernando-portfolio`

## Python

Both scripts require Python at this exact path:
```
C:\Users\panic\AppData\Local\Programs\Python\Python314\python.exe
```

If Python is updated or moved, both scheduled tasks must be re-registered
with the new path.

## Machine State

- The computer must be **powered on** (not sleeping) at midnight for the tasks to fire on time
- `StartWhenAvailable` is enabled, so if the machine was asleep, the task runs when it wakes — but the run time will be delayed
- Network connectivity is required for `git push` and `gh issue create`
- If the machine is off all night, the update runs at next boot but the data point is late

## File Locations

| File | Purpose | Tracked in git? |
|------|---------|-----------------|
| `portfolio/ai-tracker-data.json` | Live tracker data | Yes |
| `portfolio/nightingale-intake.jsonl` | Issue intake log (written during sessions) | No |
| `scripts/update-tracker.py` | Midnight update script | Yes |
| `scripts/verify-tracker.py` | 12:15 verification script | Yes |
| `scripts/nightingale-status.json` | Last run status | No |
| `scripts/nightingale-error.json` | Double-failure alert flag | No |
| `scripts/.tracker-update.lock` | Concurrency lock | No |
| `scripts/nightingale-backups/` | JSON backups (7-day rotation) | No |
| `scripts/nightingale-archive/` | Processed intake archives | No |
| `scripts/update-tracker.log` | Combined log for both scripts | No |

## Verification

After setup, run this checklist:

```powershell
# 1. Scheduled tasks registered
Get-ScheduledTask -TaskName "Nightingale*"

# 2. Python accessible
& "C:\Users\panic\AppData\Local\Programs\Python\Python314\python.exe" --version

# 3. GitHub CLI authenticated
gh auth status

# 4. Git can push without prompting
git -C "C:\Users\panic\Downloads\erin-portfolio" push --dry-run

# 5. Bug label exists
gh label list --repo erinfernando/erin-fernando-portfolio | Select-String "bug"

# 6. Dry run the update
& "C:\Users\panic\AppData\Local\Programs\Python\Python314\python.exe" "C:\Users\panic\Downloads\erin-portfolio\scripts\update-tracker.py"

# 7. Check status file was written
Get-Content "C:\Users\panic\Downloads\erin-portfolio\scripts\nightingale-status.json"
```
