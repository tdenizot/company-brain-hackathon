// Connect each demo user's GitHub account to Scalekit AgentKit, then prove it works by
// reading the hackathon repo on their behalf. Tokens stay at Scalekit: this code never sees one.
//
//   npm run connect:github              # marc + thomas
//   npm run connect:github -- thomas    # one user
//
// Prerequisite (once, in the dashboard): AgentKit -> Connections -> GitHub; its name goes in
// GITHUB_CONNECTION_NAME (Scalekit-managed credentials are enough). Identifiers are the same
// emails as src/brain/users.py, so the Python pull reuses these connected accounts.

import { ScalekitClient, ConnectorStatus } from '@scalekit-sdk/node'
import dotenv from 'dotenv'

dotenv.config({ path: new URL('../.env', import.meta.url), quiet: true })

const USERS = {
  marc: 'marc@company-brain.demo',
  thomas: 'thomas@company-brain.demo',
}
const CONNECTION = process.env.GITHUB_CONNECTION_NAME || 'github'
const OWNER = process.env.GITHUB_OWNER || 'tdenizot'
const REPO = (process.env.GITHUB_REPOS || 'company-brain-hackathon').split(',')[0].trim()
const AUTH_TIMEOUT_MS = 10 * 60 * 1000

const missing = ['SCALEKIT_ENVIRONMENT_URL', 'SCALEKIT_CLIENT_ID', 'SCALEKIT_CLIENT_SECRET']
  .filter((name) => !process.env[name])
if (missing.length) {
  console.error(`Variables manquantes dans .env : ${missing.join(', ')}`)
  console.error('Scalekit Dashboard -> Developers -> API Credentials.')
  process.exit(1)
}

const keys = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(USERS)
const unknown = keys.filter((key) => !USERS[key])
if (unknown.length) {
  console.error(`Utilisateur inconnu : ${unknown.join(', ')} (attendu : ${Object.keys(USERS).join(', ')})`)
  process.exit(1)
}

const actions = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL,
  process.env.SCALEKIT_CLIENT_ID,
  process.env.SCALEKIT_CLIENT_SECRET,
).actions

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function account(identifier) {
  const { connectedAccount } = await actions.getConnectedAccount({ connectionName: CONNECTION, identifier })
  return connectedAccount
}

// Print every missing authorization link first, so both users can click in parallel.
async function requestAuthorization(key, identifier) {
  const { connectedAccount } = await actions.getOrCreateConnectedAccount({ connectionName: CONNECTION, identifier })
  if (connectedAccount?.status === ConnectorStatus.ACTIVE) return
  const { link } = await actions.getAuthorizationLink({ connectionName: CONNECTION, identifier })
  console.log(`[${key}] Ouvrir ce lien et autoriser GitHub avec le compte de ${key} :\n  ${link}\n`)
}

async function waitActive(identifier) {
  const deadline = Date.now() + AUTH_TIMEOUT_MS
  let current
  while (Date.now() < deadline) {
    current = await account(identifier)
    if (current?.status === ConnectorStatus.ACTIVE) return current.id
    await sleep(3000)
  }
  if (current?.status === ConnectorStatus.PENDING_VERIFICATION) {
    throw new Error('compte en PENDING_VERIFICATION : désactiver la vérification utilisateur '
      + 'de l\'environnement Scalekit, ou appeler actions.verifyConnectedAccountUser')
  }
  throw new Error(`autorisation non terminée après ${AUTH_TIMEOUT_MS / 60000} min`
    + ` (statut : ${ConnectorStatus[current?.status] ?? current?.status})`)
}

async function github(connectedAccountId, toolName, toolInput = {}) {
  const { data } = await actions.executeTool({ connectedAccountId, toolName, toolInput })
  return data
}

let failed = false
const pending = []
for (const key of keys) {
  try {
    await requestAuthorization(key, USERS[key])
    pending.push(key)
  } catch (err) {
    failed = true
    console.error(`[${key}] échec : ${err.message}`)
  }
}
for (const key of pending) {
  try {
    const accountId = await waitActive(USERS[key])
    const me = await github(accountId, 'github_user_get_authenticated')
    const repo = await github(accountId, 'github_repo_get', { owner: OWNER, repo: REPO })
    console.log(`[${key}] GitHub connecté (${me?.login ?? '?'}) -> ${repo?.full_name ?? `${OWNER}/${REPO}`}`
      + ` · ${repo?.private ? 'privé' : 'public'} · branche ${repo?.default_branch ?? '?'}`)
  } catch (err) {
    failed = true
    console.error(`[${key}] échec : ${err.message}`)
  }
}
process.exit(failed ? 1 : 0)
