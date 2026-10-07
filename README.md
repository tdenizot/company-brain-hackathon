# Company Brain — Cognee × Scalekit × Respan

Projet pour le hackathon [Build a Company Brain](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-companybrain-scalekit-respan-hackathon-2026-10-07) (SF Tech Week, 2026-10-07).

Un copilote d'incident sensible aux droits d'accès, qui relie **Slack** (alertes maintenance), **GitHub** (applications) et **Notion** (projets, SOPs, CRM, planning, cahiers des charges, consignes Build).

- **Marc** (admin) : voit tout.
- **Thomas** (invité) : voit la partie projet, pas la partie commerciale.

Plan complet : [`PLAN.md`](./PLAN.md).

## Démarrage rapide

```bash
uv venv && uv pip install -e .
cp .env.example .env            # remplir la clé Respan (+ Scalekit pour le pull live)

.venv/bin/python -m brain.cli reset
.venv/bin/python -m brain.cli ingest --source sample          # données d'exemple (sans comptes SaaS)
.venv/bin/python -m brain.cli whoami --as thomas              # jeux de données lisibles
.venv/bin/python -m brain.cli ask --as thomas "Quel client est impacté par l'alerte sur portail-artisans et quel est son contrat ?"
.venv/bin/python -m brain.cli grant commercial-maison-duval-renovation --to thomas   # Marc accorde l'accès
.venv/bin/python -m brain.cli ask --as thomas "…même question…"
```

## Connecter GitHub via Scalekit (Node)

1. Scalekit Dashboard → **AgentKit → Connections** → GitHub, nommée `github` (identifiants gérés par Scalekit : pas d'OAuth app à créer).
2. Renseigner `SCALEKIT_ENVIRONMENT_URL`, `SCALEKIT_CLIENT_ID`, `SCALEKIT_CLIENT_SECRET` dans `.env` (Developers → API Credentials).
3. Lancer :

```bash
npm install
npm run connect:github              # Marc puis Thomas ; `-- thomas` pour un seul
```

Le script affiche un lien d'autorisation par utilisateur, attend que le compte passe `ACTIVE`, puis lit `GITHUB_OWNER/GITHUB_REPOS` (par défaut `tdenizot/company-brain-hackathon`) au nom de chacun. Les identifiants Scalekit sont les emails de `src/brain/users.py` : `ingest --source scalekit` réutilise ces comptes connectés.

## Structure

| Fichier | Rôle |
|---|---|
| `data/sample/` | Pull enregistré : alertes Slack, PRs/issues/workflows GitHub, pages Notion (projet + CRM) |
| `src/brain/sources/` | `sample.py` (pull enregistré) et `scalekit_pull.py` (pull live, par utilisateur) |
| `src/brain/memory.py` | Datasets Cognee par utilisateur, annuaire, grants, mode `naive` pour la baseline d'éval |
| `src/brain/agent.py` | Copilote d'incident : recall → LLM via Respan → réponse, sources, accès manquants, contradictions |
| `src/brain/cli.py` | Ligne de commande |
| `scalekit/connect-github.mjs` | Connexion GitHub par utilisateur via Scalekit AgentKit (SDK Node) |
