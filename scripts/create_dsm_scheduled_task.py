#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_TASK_DIR = Path("/usr/syno/etc/synoschedule.d/root")
DEFAULT_SYNC_COMMAND = "/usr/syno/bin/synoschedtask"


def main() -> int:
    args = parse_args()
    task_dir = Path(args.task_dir)
    task_dir.mkdir(parents=True, exist_ok=True)

    command = read_command(args.command, args.command_file)
    owner_uid = resolve_owner_uid(args.owner)
    task_id = args.task_id or next_task_id(task_dir)
    task_path = task_dir / f"{task_id}.task"

    if args.replace_name:
        replace_existing_named_task(task_dir, args.name)
    elif task_path.exists() and not args.force:
        raise SystemExit(f"{task_path} exists; pass --force or choose --task-id")

    if task_path.exists():
        backup_path(task_path)

    content = build_task_content(
        task_id=task_id,
        name=args.name,
        owner_uid=owner_uid,
        command=command,
        schedule_type=args.type,
        weekdays=args.weekdays,
        hour=args.hour,
        minute=args.minute,
        state=args.state,
        notify_enable=args.notify_enable,
        notify_if_error=args.notify_if_error,
        notify_mail=args.notify_mail,
    )
    task_path.write_text(content, encoding="utf-8")

    if not args.no_sync:
        run_sync(args.sync_command)

    print(f"created DSM task id={task_id} name={args.name} path={task_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a DSM UI-visible scheduled task.")
    parser.add_argument("--name", required=True, help="DSM task name.")
    parser.add_argument("--owner", default="root", help="Task owner username or numeric uid.")
    parser.add_argument("--command", default=None, help="Command/script text to run.")
    parser.add_argument("--command-file", default=None, help="Read command/script text from file.")
    parser.add_argument("--type", choices=["daily", "weekly"], default="weekly")
    parser.add_argument("--weekdays", default="Mon,Tue,Wed,Thu,Fri")
    parser.add_argument("--hour", type=int, required=True)
    parser.add_argument("--minute", type=int, required=True)
    parser.add_argument("--state", choices=["enabled", "disabled"], default="enabled")
    parser.add_argument("--task-id", type=int, default=None)
    parser.add_argument("--task-dir", default=str(DEFAULT_TASK_DIR))
    parser.add_argument("--sync-command", default=DEFAULT_SYNC_COMMAND)
    parser.add_argument("--notify-enable", action="store_true")
    parser.add_argument("--notify-if-error", action="store_true")
    parser.add_argument("--notify-mail", default="")
    parser.add_argument("--replace-name", action="store_true", default=True)
    parser.add_argument("--no-replace-name", dest="replace_name", action="store_false")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-sync", action="store_true")
    return parser.parse_args()


def read_command(command: str | None, command_file: str | None) -> str:
    if command_file:
        return Path(command_file).read_text(encoding="utf-8").strip()
    if command:
        return command.strip()
    raise SystemExit("provide --command or --command-file")


def resolve_owner_uid(owner: str) -> int:
    if owner.isdigit():
        return int(owner)
    import pwd

    return pwd.getpwnam(owner).pw_uid


def next_task_id(task_dir: Path) -> int:
    ids = []
    for path in task_dir.glob("*.task"):
        try:
            ids.append(int(path.stem))
        except ValueError:
            continue
    return max(ids, default=0) + 1


def replace_existing_named_task(task_dir: Path, name: str) -> None:
    for path in task_dir.glob("*.task"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"^name={re.escape(name)}$", text, flags=re.MULTILINE):
            backup_path(path)
            path.unlink()


def backup_path(path: Path) -> Path:
    backup = path.with_suffix(
        path.suffix + ".bak.dsm-task-scheduler_" + datetime.now().strftime("%Y%m%d%H%M%S")
    )
    shutil.copy2(path, backup)
    return backup


def build_task_content(
    *,
    task_id: int,
    name: str,
    owner_uid: int,
    command: str,
    schedule_type: str,
    weekdays: str,
    hour: int,
    minute: int,
    state: str,
    notify_enable: bool,
    notify_if_error: bool,
    notify_mail: str,
) -> str:
    if not 0 <= hour <= 23:
        raise ValueError("--hour must be 0-23")
    if not 0 <= minute <= 59:
        raise ValueError("--minute must be 0-59")

    week_bits = week_string(weekdays)
    command_b64 = base64.b64encode(command.encode("utf-8")).decode("ascii")
    app_args = json.dumps(
        {
            "notify_enable": notify_enable,
            "notify_if_error": notify_if_error,
            "notify_mail": notify_mail,
            "script": command,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    action = command.replace("\n", " ")
    return f"""id={task_id}
last work hour={hour}
can edit owner=1
can delete from ui=1
edit dialog=SYNO.SDS.TaskScheduler.EditDialog
type={schedule_type}
action=#common:run#: {action}
systemd slice=
monthly week=0
can edit from ui=1
week={week_bits}
app name=#common:command_line#
name={name}
can run app same time=1
owner={owner_uid}
repeat min store config=[1,5,10,15,20,30]
repeat hour store config=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
simple edit form=1
repeat hour=0
listable=1
app args={app_args} 
state={state}
can run task same time=0
start day=0
cmd={command_b64}
run hour={hour}
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min={minute}
start month=0
can edit name=1
start year=0
can run from ui=1
repeat min=0
cmdArgv=
"""


def week_string(weekdays: str) -> str:
    aliases = {
        "sun": 0,
        "sunday": 0,
        "mon": 1,
        "monday": 1,
        "tue": 2,
        "tues": 2,
        "tuesday": 2,
        "wed": 3,
        "wednesday": 3,
        "thu": 4,
        "thur": 4,
        "thurs": 4,
        "thursday": 4,
        "fri": 5,
        "friday": 5,
        "sat": 6,
        "saturday": 6,
    }
    bits = ["0"] * 7
    for raw in re.split(r"[, ]+", weekdays.strip()):
        if not raw:
            continue
        key = raw.lower()
        if "-" in key:
            start, end = key.split("-", 1)
            start_idx = aliases[start]
            end_idx = aliases[end]
            idx = start_idx
            while True:
                bits[idx] = "1"
                if idx == end_idx:
                    break
                idx = (idx + 1) % 7
            continue
        bits[aliases[key]] = "1"
    if "1" not in bits:
        raise ValueError("--weekdays resolved to no days")
    return "".join(bits)


def run_sync(sync_command: str) -> None:
    subprocess.run([sync_command, "--sync"], check=True)
    for command in (
        ["/usr/syno/sbin/synoservice", "--restart", "crond"],
        ["/usr/syno/bin/synosystemctl", "restart", "crond"],
    ):
        if Path(command[0]).exists():
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            break


if __name__ == "__main__":
    raise SystemExit(main())
