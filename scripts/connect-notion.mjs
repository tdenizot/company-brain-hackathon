// Connect a demo user's Notion through Scalekit AgentKit, then check which Notion workspace
// was actually authorized. Uses the same identifier as src/brain/sources/scalekit_pull.py
// (the user's email), so the Python pull reuses this connected account.
//
//   node scripts/connect-notion.mjs --as marc            # authorize if needed, then verify
//   node scripts/connect-notion.mjs --as thomas --reset  # drop the account and re-authorize

import { createInterface } from 'node:readline/promises'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'

import { ConnectorStatus, ScalekitClient, ScalekitNotFoundException } from '@scalekit-sdk/node'
import dotenv from 'dotenv'

dotenv.config({ path: fileURLToPath(new URL('../.env', import.meta.url)), quiet: true })

const CONNECTION = 'notion'
// Same emails as src/brain/users.py.
const USERS = { marc: 'marc@company-brain.demo', thomas: 'thomas@company-brain.demo' }
const EXPECTED_WORKSPACE = process.env.NOTION_EXPECTED_WORKSPACE || 'Hackathon Oct. 7th'

const { values: args } = parseArgs({
  options: { as: { type: 'string', default: 'marc' }, reset: { type: 'boolean', default: false } },
})
const identifier = USERS[args.as]
if (!identifier) {
  console.error(`--as doit valoir : ${Object.keys(USERS).join(', ')}`)
  process.exit(2)
}

const missing = ['SCALEKIT_ENVIRONMENT_URL', 'SCALEKIT_CLIENT_ID', 'SCALEKIT_CLIENT_SECRET'].filter((v) => !process.env[v])
if (missing.length) {
  console.error(`Variables manquantes dans .env : ${missing.join(', ')} (voir .env.example).`)
  process.exit(2)
}

const actions = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL,
  process.env.SCALEKIT_CLIENT_ID,
  process.env.SCALEKIT_CLIENT_SECRET,
).actions
const account = { connectionName: CONNECTION, identifier }

async function accountStatus() {
  try {
    return (await actions.getConnectedAccount(account)).connectedAccount?.status
  } catch (e) {
    if (e instanceof ScalekitNotFoundException) return undefined
    throw e
  }
}

// Tool responses are the raw Notion payload; look a key up wherever it sits.
function find(obj, key) {
  if (!obj || typeof obj !== 'object') return undefined
  if (key in obj) return obj[key]
  for (const v of Object.values(obj)) {
    const hit = find(v, key)
    if (hit !== undefined) return hit
  }
}

function title(result) {
  const rich = result.title ?? Object.values(result.properties ?? {}).find((p) => p.type === 'title')?.title ?? []
  return rich.map((t) => t.plain_text).join('') || '(sans titre)'
}

if (args.reset && (await accountStatus()) !== undefined) {
  await actions.deleteConnectedAccount(account)
  console.log(`Compte Notion supprimé pour ${identifier}.`)
}

if ((await accountStatus()) !== ConnectorStatus.ACTIVE) {
  const { link } = await actions.getAuthorizationLink(account)
  console.log(`\nAutoriser Notion pour ${identifier} :\n${link}\n`)
  console.log(`Sur l'écran Notion : choisir l'espace « ${EXPECTED_WORKSPACE} » dans le sélecteur en haut à droite,`)
  console.log('puis cocher les pages à partager avec l\'intégration.\n')
  const rl = createInterface({ input: process.stdin, output: process.stdout })
  await rl.question('Entrée une fois l\'autorisation faite… ')
  rl.close()
  if ((await accountStatus()) !== ConnectorStatus.ACTIVE) {
    console.error('Le compte Notion n\'est toujours pas actif.')
    process.exit(1)
  }
}

const self = await actions.executeTool({ connector: CONNECTION, identifier, toolName: 'notion_user_get_self', toolInput: {} })
const workspace = find(self.data, 'workspace_name')
if (!workspace?.toLowerCase().includes(EXPECTED_WORKSPACE.toLowerCase())) {
  console.error(`✗ Mauvais espace Notion pour ${identifier} : « ${workspace ?? 'inconnu'} » (attendu : « ${EXPECTED_WORKSPACE} »).`)
  console.error(`  Relancer avec --reset et choisir le bon espace sur l'écran Notion.`)
  process.exit(1)
}
console.log(`✓ Notion connecté pour ${identifier} sur l'espace « ${workspace} ».`)

const search = await actions.executeTool({ connector: CONNECTION, identifier, toolName: 'notion_data_fetch', toolInput: { page_size: 20 } })
const results = find(search.data, 'results') ?? []
console.log(`${results.length} page(s)/base(s) partagée(s) avec l'intégration${results.length === 20 ? ' (20 premières)' : ''} :`)
for (const r of results) console.log(`  - [${r.object}] ${title(r)}`)
if (!results.length) console.log('  Aucune : relancer avec --reset et cocher les pages à partager.')
