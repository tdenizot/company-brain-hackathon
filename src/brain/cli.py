"""Company Brain CLI.

  python -m brain.cli reset
  python -m brain.cli ingest [--source sample|scalekit] [--mode secure|naive] [--improve]
  python -m brain.cli ask --as thomas "Quel client est impacté par l'alerte sur portail-artisans ?"
  python -m brain.cli grant marc-commercial --to thomas
  python -m brain.cli whoami --as thomas
"""

import argparse
import asyncio
import json
import shutil

from .config import ROOT


def main():
    p = argparse.ArgumentParser(prog="brain")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reset")
    ing = sub.add_parser("ingest")
    ing.add_argument("--source", choices=["sample", "scalekit"], default="sample")
    ing.add_argument("--mode", choices=["secure", "naive"], default="secure")
    ing.add_argument("--improve", action="store_true")
    ask = sub.add_parser("ask")
    ask.add_argument("--as", dest="user", choices=["marc", "thomas"], required=True)
    ask.add_argument("question")
    gr = sub.add_parser("grant")
    gr.add_argument("dataset")
    gr.add_argument("--to", required=True)
    gr.add_argument("--owner", default="marc")
    who = sub.add_parser("whoami")
    who.add_argument("--as", dest="user", choices=["marc", "thomas"], required=True)
    args = p.parse_args()

    if args.cmd == "reset":
        for d in (".cognee_system", ".cognee_data"):
            shutil.rmtree(ROOT / d, ignore_errors=True)
        print("Mémoire Cognee effacée.")
        return
    asyncio.run(run(args))


async def run(args):
    from . import memory
    from .users import USERS

    if args.cmd == "ingest":
        if args.source == "sample":
            from .sources.sample import pull
        else:
            from .sources.scalekit_pull import pull
        pulls = {key: pull(u) for key, u in USERS.items()}
        for key, docs in pulls.items():
            print(f"pull {args.source} pour {key} : {len(docs)} docs")
        await memory.ingest(pulls, mode=args.mode, improve=args.improve)
    elif args.cmd == "grant":
        await memory.grant(args.owner, args.dataset, args.to)
    elif args.cmd == "whoami":
        print([d.name for d in await memory.readable(args.user)])
    elif args.cmd == "ask":
        from .agent import ask

        print(json.dumps(await ask(args.user, args.question), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
