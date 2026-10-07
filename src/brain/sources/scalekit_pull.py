"""Live pull through Scalekit AgentKit, on behalf of one user (their identifier).
Returns the same Doc shapes as sources/sample.py."""

import os

from scalekit import ScalekitClient

from ..docs import Doc
from ..users import DemoUser

SLACK_CHANNEL = os.environ.get("SLACK_ALERT_CHANNEL", "#alertes-maintenance")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")
GITHUB_REPOS = [r for r in os.environ.get("GITHUB_REPOS", "").split(",") if r]


def client():
    return ScalekitClient(
        env_url=os.environ["SCALEKIT_ENVIRONMENT_URL"],
        client_id=os.environ["SCALEKIT_CLIENT_ID"],
        client_secret=os.environ["SCALEKIT_CLIENT_SECRET"],
    ).actions


def ensure_connected(actions, connection: str, identifier: str) -> None:
    account = actions.get_or_create_connected_account(connection_name=connection, identifier=identifier)
    if account.connected_account.status != "ACTIVE":
        link = actions.get_authorization_link(connection_name=connection, identifier=identifier)
        print(f"Autoriser {connection} pour {identifier} : {link.link}")
        input("Entrée une fois l'autorisation faite… ")


def _run(actions, connection: str, identifier: str, tool: str, **tool_input):
    return actions.execute_tool(tool_name=tool, tool_input=tool_input, connection_name=connection, identifier=identifier).data


def pull(user: DemoUser) -> list[Doc]:
    actions = client()
    for conn in ("slack", "github", "notion"):
        ensure_connected(actions, conn, user.email)

    docs: list[Doc] = []

    history = _run(actions, "slack", user.email, "slack_fetch_conversation_history", channel=SLACK_CHANNEL, limit=200)
    lines = [f"[{SLACK_CHANNEL} · {m.get('user')} · {m.get('ts')}] {m.get('text')}" for m in reversed(history["messages"])]
    docs.append(Doc("slack", "alerte", f"Alertes {SLACK_CHANNEL}", "toutes", "UptimeBot", "projet", "\n".join(lines)))

    for repo in GITHUB_REPOS:
        for pr in _run(actions, "github", user.email, "github_pull_requests_list", owner=GITHUB_OWNER, repo=repo, state="all"):
            docs.append(Doc("github", "pull_request", f"{repo} #{pr['number']} — {pr['title']}", repo,
                            pr["user"]["login"], "projet", pr.get("body") or ""))
        for issue in _run(actions, "github", user.email, "github_issues_list", owner=GITHUB_OWNER, repo=repo, state="all"):
            docs.append(Doc("github", "issue", f"{repo} #{issue['number']} — {issue['title']}", repo,
                            issue["user"]["login"], "projet", issue.get("body") or ""))

    # TODO(notion): tool names to confirm with actions.list_tools(connection_name="notion")
    # once the connection exists, and map each page to section projet/commercial.
    return docs
