"""The incident copilot: recall from the datasets the user may read, answer with an LLM
through the Respan gateway, and flag what the user could not see (access gaps)."""

import json
import os

import cognee
from openai import AsyncOpenAI

from .config import AGENT_MODEL, RESPAN_BASE_URL
from .memory import readable
from .users import USERS

SYSTEM_PROMPT = """Tu es le Company Brain d'une agence qui développe et maintient des applications pour ses clients.
Tu aides {name} à traiter les alertes de maintenance en croisant Slack (alertes), GitHub (code, PRs, issues) et Notion (projets, SOPs, cahiers des charges, consignes Build, planning, CRM).

Règles :
- Réponds UNIQUEMENT à partir du CONTEXTE ci-dessous. N'invente rien.
- Cite tes sources sous la forme source:slack / source:github / source:notion (le contexte porte ces en-têtes).
- Si le contexte contient des entrées « Annuaire » indiquant qu'une information utile existe mais en accès restreint,
  ne devine pas son contenu : signale-la dans access_gaps avec le responsable à qui demander l'accès.
- Si deux sources se contredisent (ex. consignes Build vs workflow GitHub, cahier des charges vs code), signale-le dans contradictions.
- Réponds en français, de façon concise et actionnable.

Réponds en JSON : {{"answer": str, "sources": [str], "access_gaps": [{{"sujet": str, "responsable": str}}], "contradictions": [str]}}

CONTEXTE :
{context}"""


def _llm() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=RESPAN_BASE_URL, api_key=os.environ["RESPAN_API_KEY"])


def _text(entry) -> str:
    for attr in ("text", "context", "answer"):
        value = getattr(entry, attr, None)
        if value:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return str(entry)


async def retrieve(user_key: str, question: str) -> tuple[list[str], str]:
    from .users import cognee_user

    user = await cognee_user(user_key)
    datasets = await readable(user_key)
    if not datasets:
        return [], ""
    results = await cognee.recall(question, dataset_ids=[d.id for d in datasets], user=user, only_context=True)
    return [d.name for d in datasets], "\n\n".join(_text(r) for r in results)


async def ask(user_key: str, question: str) -> dict:
    datasets, context = await retrieve(user_key, question)
    response = await _llm().chat.completions.create(
        model=AGENT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(name=USERS[user_key].name, context=context or "(vide)")},
            {"role": "user", "content": question},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    result.update(as_user=user_key, datasets=datasets)
    return result
