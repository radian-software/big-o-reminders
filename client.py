#!/usr/bin/env python3

import json
import http.client
import os
import pathlib
import re
import socket
import subprocess
import sys
import time
import uuid


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def post_json(endpoint, body):
    host = os.environ["BIG_O_REMINDERS_HOST"]
    port = int(os.environ["BIG_O_REMINDERS_PORT"])
    path = "/reminders/" + endpoint
    conn = http.client.HTTPSConnection(host, port=port)
    headers = {"Content-Type": "application/json"}
    body_str = json.dumps(body)
    conn.request("POST", path, body_str, headers)
    resp = conn.getresponse()
    if resp.status == 200:
        resp_str = resp.read().decode()
        return json.loads(resp_str)
    elif resp.status == 204:
        return None
    else:
        die("got http status {}".format(resp.status))


if len(sys.argv) == 1:
    hostname = socket.gethostname()
    data = post_json("get", {"hostname": hostname})
    assert isinstance(data, list)
    reminders = [r["reminder"] for r in data]
    uuids = [r["uuid"] for r in data]

    if os.environ.get("SYSTEM") == "macOS":
        for reminder in reminders:
            subprocess.run(
                [
                    "terminal-notifier",
                    "-title",
                    "Big-O Notifications",
                    "-message",
                    "\\{}".format(reminder),
                ]
            )
        post_json("delete", {"hostname": hostname, "uuids": uuids})
    else:
        shown_reminders = set()
        for line in (
            subprocess.run(
                "ps -e -o args | (grep '^zenity' || true)",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
            )
            .stdout.decode()
            .splitlines()
        ):
            m = re.search(r"--text=O\((.*)\)$", line)
            if not m:
                continue
            shown_reminders.add(m.group(1))
        for r in data:
            reminder = r["reminder"]
            escaped = reminder.replace("&", "&amp;")
            if escaped in shown_reminders:
                continue
            if os.fork() == 0:
                start = time.time()
                subprocess.run(
                    [
                        "timeout",
                        "7200",
                        "zenity",
                        "--info",
                        "--width=300",
                        "--title=Big-O Reminders",
                        f"--text=O({escaped})",
                    ],
                    check=True,
                )
                duration = time.time() - start
                if duration >= 1:
                    post_json("delete", {"hostname": hostname, "uuids": [r["uuid"]]})
                sys.exit(0)
elif len(sys.argv) == 3:
    assert " " not in sys.argv[1]
    post_json("post", {"reminder": sys.argv[2], "hostname": sys.argv[1]})
else:
    print("usage: big-o-reminders [HOSTNAME REMINDER]")
    sys.exit(1)
