#!/usr/bin/env python3

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import uuid

import flask

logging.basicConfig(level=logging.INFO)


class Reminder:
    def __init__(self, text, hostname_allowlist=None, timeout=None):
        self.text = text
        self.uuid = str(uuid.uuid4())
        self.time = datetime.now()
        self.hostname_allowlist = set()
        self.hostname_denylist = set()
        if hostname_allowlist:
            self.hostname_allowlist |= set(hostname_allowlist)
        self.timeout = timeout or timedelta(hours=1)

    def is_stale(self):
        age = datetime.now() - self.time
        # We have delivered to at least one host, and it's been at
        # least a day since then.
        return self.hostname_denylist and age > self.timeout

    @classmethod
    def loads(cls, obj):
        r = cls(obj["text"])
        r.uuid = obj["uuid"]
        r.time = datetime.fromtimestamp(obj["time"])
        r.timeout = timedelta(seconds=obj["timeout"])
        r.hostname_allowlist = set(obj["hostname_allowlist"])
        r.hostname_denylist = set(obj["hostname_denylist"])
        return r

    def dumps(self):
        return {
            "text": self.text,
            "uuid": self.uuid,
            "time": self.time.timestamp(),
            "timeout": self.timeout.total_seconds(),
            "hostname_allowlist": list(self.hostname_allowlist),
            "hostname_denylist": list(self.hostname_denylist),
        }


class ReminderList:
    def __init__(self):
        self.reminders = []

    def load(self):
        try:
            with open("reminders.json") as f:
                self.reminders = [Reminder.loads(r) for r in json.load(f)]
        except Exception as e:
            logging.error(f"Failed to load reminders from disk: {e}")

    def dump(self):
        with open("reminders.json.tmp", "w") as f:
            json.dump([r.dumps() for r in self.reminders], f, indent=2)
            f.write("\n")
        Path("reminders.json.tmp").rename("reminders.json")

    def post(self, reminder_text, hostname_allowlist=None, timeout=None):
        reminder = Reminder(
            reminder_text, hostname_allowlist=hostname_allowlist, timeout=timeout,
        )
        logging.info(f"POST {repr(reminder_text)} for={hostname_allowlist or 'any'}")
        self.reminders.append(reminder)

    def get(self, hostname):
        # Side effect of cleaning up stale reminders, so we don't need
        # a separate job for that
        old_len = len(self.reminders)
        self.reminders = [r for r in self.reminders if not r.is_stale()]
        messages = []
        for reminder in self.reminders:
            if (
                reminder.hostname_allowlist
                and hostname not in reminder.hostname_allowlist
            ):
                continue
            if hostname in reminder.hostname_denylist:
                continue
            messages.append({"reminder": reminder.text, "uuid": reminder.uuid})
        return messages

    def delete(self, hostname, uuids):
        uuids = set(uuids)
        for reminder in self.reminders:
            if reminder.uuid in uuids:
                logging.info(f"DELETE {repr(reminder.text)} for={hostname}")
                reminder.hostname_denylist.add(hostname)
                reminder.time = datetime.now()

    @property
    def count(self):
        return len(self.reminders)


app = flask.Flask(__name__)
app.reminders = ReminderList()
app.reminders.load()


@app.route("/reminders/post", methods=["POST"])
def post():
    try:
        reminder_text = flask.request.json["reminder"]
        hostname = flask.request.json.get("hostname")
        timeout = flask.request.json.get("timeout")
        if timeout:
            timeout = timedelta(seconds=int(timeout))
        else:
            timeout = None
    except Exception as e:
        return (str(e), 400)
    allowlist = None
    if hostname:
        allowlist = [hostname]
    app.reminders.post(reminder_text, hostname_allowlist=allowlist, timeout=timeout)
    app.reminders.dump()
    return ("", 204)


@app.route("/reminders/get", methods=["POST"])
def get():
    try:
        hostname = flask.request.json["hostname"]
    except Exception as e:
        return (str(e), 400)
    old_count = app.reminders.count
    res = app.reminders.get(hostname)
    if app.reminders.count < old_count:
        # We deleted some, save that to disk
        app.reminders.dump()
    return flask.jsonify(res)


@app.route("/reminders/delete", methods=["POST"])
def delete():
    try:
        hostname = flask.request.json["hostname"]
        uuids = flask.request.json["uuids"]
    except Exception as e:
        return (str(e), 400)
    app.reminders.delete(hostname, uuids)
    app.reminders.dump()
    return ("", 204)


@app.route("/health")
def health():
    return ("healthy", 200)
