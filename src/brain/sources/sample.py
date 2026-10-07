"""Recorded pull: the same Doc shapes the Scalekit pull produces, from data/sample/*.json.
Lets judges (and us, before Scalekit is wired) run everything without SaaS accounts."""

import json

from ..config import SAMPLE_DIR
from ..docs import Doc
from ..users import DemoUser

APPS = ("portail-artisans", "suivi-chantier", "agent-rh")


def _slack() -> list[Doc]:
    data = json.loads((SAMPLE_DIR / "slack.json").read_text())
    # One document per app: an alert and the replies that follow it stay together.
    threads: dict[str, list[str]] = {}
    current = "toutes"
    for m in data["messages"]:
        current = next((a for a in APPS if a in m["text"]), current)
        threads.setdefault(current, []).append(f"[{data['channel']} · {m['user']} · {m['ts']}] {m['text']}")
    return [
        Doc("slack", "alerte", f"Alertes {data['channel']} — {app}", app, "UptimeBot", "projet", "\n".join(lines))
        for app, lines in threads.items()
    ]


def _github() -> list[Doc]:
    items = json.loads((SAMPLE_DIR / "github.json").read_text())["items"]
    docs = []
    for i in items:
        ref = f"#{i['number']}" if "number" in i else i["path"]
        state = f" · état : {i['state']}" if "state" in i else ""
        title = f"{i['repo']} {ref} — {i.get('title', i.get('path'))}"
        body = f"Auteur : {i['author']} · date : {i['date']}{state}\n{i['body']}"
        docs.append(Doc("github", i["kind"], title, i["repo"], i["author"], "projet", body))
    return docs


def _notion() -> list[Doc]:
    pages = json.loads((SAMPLE_DIR / "notion.json").read_text())["pages"]
    return [Doc("notion", p["type"], p["title"], p["app"], p["owner"], p["section"], p["body"]) for p in pages]


def pull(user: DemoUser) -> list[Doc]:
    """What this user's own connections would return. A Notion guest never receives the
    commercial pages, exactly like the live API."""
    return [d for d in _slack() + _github() + _notion() if d.section in user.sections]
