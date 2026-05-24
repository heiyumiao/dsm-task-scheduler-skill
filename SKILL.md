---
name: dsm-task-scheduler
description: Create, inspect, and repair Synology DSM Task Scheduler jobs that are visible in the DSM Control Panel Task Scheduler UI. Use when the user asks to add a DSM scheduled task, make a cron job show in DSM UI, write /usr/syno/etc/synoschedule.d task files, sync synoschedtask, configure Synology logs for scheduled scripts, or troubleshoot DSM tasks not appearing.
---

# DSM Task Scheduler

Use this skill for Synology DSM scheduled tasks that should appear in the DSM
Control Panel UI. Prefer DSM scheduler tasks over raw `/etc/crontab` entries
unless the user explicitly wants a hidden system cron job.

## Workflow

1. Confirm the SSH target and script command.
2. Put long commands in a wrapper script on the NAS. The wrapper should:
   - `cd` to its app directory.
   - create a `logs/` directory.
   - append stdout/stderr to a dated log file.
   - use a lock directory in `/tmp` to avoid concurrent duplicate runs.
3. Inspect existing DSM tasks:

```bash
sudo /usr/syno/bin/synoschedtask --get
sudo ls /usr/syno/etc/synoschedule.d/root/*.task
```

4. Create or update a UI-visible task with
   `scripts/create_dsm_scheduled_task.py`.
5. Run `sudo /usr/syno/bin/synoschedtask --sync`.
6. Verify:

```bash
sudo /usr/syno/bin/synoschedtask --get id=<id>
sudo grep -n "synoschedtask --run id=<id>" /etc/crontab
```

## Helper Usage

Copy the helper to the NAS and run it with `sudo python3`:

```bash
scp scripts/create_dsm_scheduled_task.py ttlocal:/tmp/
ssh ttlocal "printf '%s\n' '/path/to/run_task.sh' > /tmp/dsm_task_cmd.txt"
ssh ttlocal "sudo python3 /tmp/create_dsm_scheduled_task.py \
  --name futu-ashare-daily \
  --owner codex_ssh \
  --type weekly \
  --weekdays Mon,Tue,Wed,Thu,Fri \
  --hour 16 \
  --minute 35 \
  --command-file /tmp/dsm_task_cmd.txt"
```

The helper writes `/usr/syno/etc/synoschedule.d/root/<id>.task`, backs up an
existing task with the same name, syncs DSM scheduler, and prints the created
task id.

## Synology Details

- UI task files live under `/usr/syno/etc/synoschedule.d/root/*.task` on DSM 7.
- `week=` is a 7-character Sunday-to-Saturday bit string:
  - `1000000` = Sunday
  - `0111110` = Monday-Friday
  - `1111111` = every day
- For custom scripts, use:
  - `app=SYNO.SDS.TaskScheduler.Script`
  - `app name=#common:command_line#`
  - `edit form=SYNO.SDS.TaskScheduler.Script.FormPanel`
  - `cmd=<base64 of command>`
  - `app args=<JSON containing script>`
- The generated `/etc/crontab` line normally runs as `root` and calls
  `synoschedtask --run id=<id>`; DSM handles the task owner.

## Safety

- Back up existing `.task` files before overwriting.
- Do not remove unrelated `/etc/crontab` lines.
- After migrating a raw cron entry to DSM UI, remove only the duplicate raw
  entry for the same command to avoid double execution.
- Verify logs by running the wrapper manually once before relying on schedule.
