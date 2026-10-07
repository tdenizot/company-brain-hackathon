"""The two demo users. The Scalekit identifier is the Cognee user's email."""

from dataclasses import dataclass

from . import config  # noqa: F401  (env before cognee)
from cognee.modules.engine.operations.setup import setup
from cognee.modules.users.methods import create_user, get_user_by_email


@dataclass(frozen=True)
class DemoUser:
    key: str
    email: str
    name: str
    sections: frozenset[str]  # Notion sections this user can see natively


USERS = {
    "marc": DemoUser("marc", "marc@company-brain.demo", "Marc", frozenset({"projet", "commercial"})),
    "thomas": DemoUser("thomas", "thomas@company-brain.demo", "Thomas", frozenset({"projet"})),
}


_ready = False


async def cognee_user(key: str):
    global _ready
    if not _ready:  # relational DB + tables must exist before the first user lookup
        await setup()
        _ready = True
    u = USERS[key]
    return await get_user_by_email(u.email) or await create_user(u.email, "hackathon-pw", is_verified=True)
