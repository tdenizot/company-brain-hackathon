"""Common document shape for everything pulled from Slack, GitHub and Notion.

Every source is converted to `Doc` before it reaches Cognee, so the sample data and the
live Scalekit pull are interchangeable."""

from dataclasses import dataclass


@dataclass
class Doc:
    source: str      # slack | github | notion
    kind: str        # alerte | pull_request | issue | file | projet | sop | crm | ...
    title: str
    app: str         # portail-artisans | suivi-chantier | agent-rh | toutes
    owner: str
    section: str     # projet | commercial — the access boundary
    body: str

    @property
    def tags(self) -> list[str]:
        return [f"source:{self.source}", f"type:{self.kind}", f"app:{self.app}", f"section:{self.section}"]

    def render(self) -> str:
        """Text sent to Cognee. The header keeps provenance visible to the LLM so it can cite."""
        return f"[source:{self.source} · type:{self.kind} · app:{self.app} · owner:{self.owner}] {self.title}\n{self.body}"
