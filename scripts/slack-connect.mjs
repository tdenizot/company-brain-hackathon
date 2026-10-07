// Connect one user's Slack (workspace SLACK_WORKSPACE) through Scalekit AgentKit,
// then check the token really points at that workspace and read the alert channel.
//   npm run slack:connect                       # as marc@company-brain.demo
//   SCALEKIT_IDENTIFIER=thomas@company-brain.demo npm run slack:connect

import 'dotenv/config';
import { createInterface } from 'node:readline/promises';
import { ConnectorStatus, ScalekitClient } from '@scalekit-sdk/node';

const required = ['SCALEKIT_ENVIRONMENT_URL', 'SCALEKIT_CLIENT_ID', 'SCALEKIT_CLIENT_SECRET'];
const missing = required.filter((name) => !process.env[name]);
if (missing.length) {
  console.error(`Variables manquantes dans .env : ${missing.join(', ')}`);
  process.exit(1);
}

const connectionName = process.env.SLACK_CONNECTION_NAME || 'slack';
const identifier = process.env.SCALEKIT_IDENTIFIER || 'marc@company-brain.demo';
const workspace = process.env.SLACK_WORKSPACE || 'Gemlia';
const channel = process.env.SLACK_ALERT_CHANNEL || '#alertes-maintenance';

const actions = new ScalekitClient(
  process.env.SCALEKIT_ENVIRONMENT_URL,
  process.env.SCALEKIT_CLIENT_ID,
  process.env.SCALEKIT_CLIENT_SECRET,
).actions;

let { connectedAccount: account } = await actions.getOrCreateConnectedAccount({ connectionName, identifier });

if (account?.status !== ConnectorStatus.ACTIVE) {
  const { link } = await actions.getAuthorizationLink({ connectionName, identifier });
  console.log(`Ouvre ce lien, choisis le workspace "${workspace}" en haut à droite et autorise :\n${link}`);
  if (!process.stdin.isTTY) {
    console.log("Relance le script une fois l'autorisation faite.");
    process.exit(0);
  }
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  await rl.question("Entrée une fois l'autorisation faite… ");
  rl.close();

  ({ connectedAccount: account } = await actions.getConnectedAccount({ connectionName, identifier }));
  if (account?.status !== ConnectorStatus.ACTIVE) {
    console.error(`Compte ${ConnectorStatus[account?.status] ?? 'introuvable'}, pas ACTIVE. Relance le script.`);
    process.exit(1);
  }
}

const { data: auth } = await actions.executeTool({
  toolName: 'slack_auth_test',
  toolInput: {},
  connectedAccountId: account.id,
});
console.log(`Connecté à Slack : workspace "${auth.team}" (${auth.team_id}), utilisateur ${auth.user}`);
if (auth.team?.toLowerCase() !== workspace.toLowerCase()) {
  console.error(`Mauvais workspace : attendu "${workspace}". Déconnecte le compte dans Scalekit et ré-autorise.`);
  process.exit(1);
}

const { data: history } = await actions.executeTool({
  toolName: 'slack_fetch_conversation_history',
  toolInput: { channel, limit: 5 },
  connectedAccountId: account.id,
});
console.log(`${history.messages?.length ?? 0} derniers messages de ${channel} :`);
for (const m of history.messages ?? []) console.log(`- [${m.user ?? m.bot_id}] ${m.text}`);
