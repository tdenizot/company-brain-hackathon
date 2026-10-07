"""Cognee side: datasets, ingestion, grants.

secure mode (the real design):
  marc-projet                    Marc's project-side pull
  commercial-<client>            Marc's CRM pages, one dataset per client (least-privilege grants)
  thomas-projet                  Thomas's own pull (guest: no commercial pages)
  annuaire                       metadata only (what exists, who owns it), readable by everyone
naive mode (eval baseline): one dataset, everything, shared with everyone, no tags.
"""

import re
import unicodedata

import cognee
from cognee.modules.data.methods import get_authorized_existing_datasets
from cognee.modules.users.permissions.methods import authorized_give_permission_on_datasets
from cognee.tasks.ingestion.data_item import DataItem

from .docs import Doc
from .users import USERS, cognee_user


def _items(docs: list[Doc], tagged: bool) -> list[DataItem]:
    return [DataItem(d.render(), label=d.title, node_set=d.tags if tagged else None, literal_text=True) for d in docs]


def directory_entries(docs: list[Doc]) -> list[Doc]:
    """Existence + owner of restricted content, never the content itself."""
    return [
        Doc("annuaire", "annuaire", f"Annuaire — {d.title}", d.app, d.owner, "projet",
            f"Il existe une fiche « {d.title} » dans la partie {d.section} de Notion, liée à l'application {d.app}. "
            f"Elle contient des informations commerciales (contact client, contrat, montants, renouvellement, santé du compte). "
            f"Accès restreint (jeu de données {commercial_dataset(d)}). Responsable à qui demander l'accès : {d.owner}.")
        for d in docs if d.section == "commercial"
    ]


def commercial_dataset(doc: Doc) -> str:
    """'CRM — Maison Duval Rénovation' -> 'commercial-maison-duval-renovation'."""
    client = doc.title.split("—", 1)[-1]
    ascii_name = unicodedata.normalize("NFKD", client).encode("ascii", "ignore").decode()
    return "commercial-" + re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


async def remember(docs: list[Doc], dataset: str, owner_key: str, tagged: bool = True, improve: bool = False):
    if not docs:
        return
    user = await cognee_user(owner_key)
    print(f"  remember → {dataset} ({len(docs)} docs, owner {owner_key})")
    await cognee.remember(_items(docs, tagged), dataset_name=dataset, user=user, self_improvement=improve)


async def grant(owner_key: str, dataset: str, to_key: str, permission: str = "read"):
    owner, grantee = await cognee_user(owner_key), await cognee_user(to_key)
    (ds,) = await get_authorized_existing_datasets([dataset], "share", owner)
    await authorized_give_permission_on_datasets(grantee.id, [ds.id], permission, owner.id)
    print(f"  grant {permission} : {dataset} ({owner_key}) → {to_key}")


async def readable(user_key: str):
    return await get_authorized_existing_datasets(None, "read", await cognee_user(user_key))


async def ingest(pulls: dict[str, list[Doc]], mode: str = "secure", improve: bool = False):
    marc_docs = pulls["marc"]
    if mode == "naive":
        await remember(marc_docs, "naive-all", "marc", tagged=False)
        await grant("marc", "naive-all", "thomas")
        return

    await remember([d for d in marc_docs if d.section == "projet"], "marc-projet", "marc", improve=improve)
    commercial: dict[str, list[Doc]] = {}
    for d in marc_docs:
        if d.section == "commercial":
            commercial.setdefault(commercial_dataset(d), []).append(d)
    for dataset, docs in commercial.items():
        await remember(docs, dataset, "marc", improve=improve)
    await remember(pulls["thomas"], "thomas-projet", "thomas", improve=improve)
    await remember(directory_entries(marc_docs), "annuaire", "marc", improve=improve)
    await grant("marc", "annuaire", "thomas")


async def reset():
    await cognee.forget(everything=True)
    for key in USERS:
        await cognee_user(key)
