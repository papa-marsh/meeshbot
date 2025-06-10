import { GroupMeMessage, periodicMessageSync, sendMessage } from './integrations/groupMe';
import { commandRegistry } from './commands/registry';
import { botUserIds } from './secrets';
import { respondWithAi } from './commands/chat';
import { checkAndSendDueReminders } from './commands/reminders';
import { syncMessageToDb } from './utils/db';
import { syncUpcomingGames } from './integrations/mlb';

export interface Env {
	DB: D1Database;
	GROUPME_TOKEN: string;
	TESTING_GROUP_ID: string;
	OPENAI_API_KEY: string;
	ANTHROPIC_API_KEY: string;
	BALLDONTLIE_API_KEY: string;
	SPORTS_MCP_SERVER_URL: string;
	SPORTS_MCP_TOKEN: string;
	MEESHBOT_MCP_SERVER_URL: string;
	MEESHBOT_MCP_TOKEN: string;
}

export interface ScheduledController {
	readonly scheduledTime: number;
	readonly cron: string;
	noRetry(): void;
}

export default {
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);
		const path = url.pathname;

		switch (path) {
			case '/groupme-webhook':
				return handleGroupMeWebhook(request, env);
			case '/mcp':
				return handleMCPRequest(request, env);
			default:
				return new Response('Not Found', { status: 404 });
		}
	},

	async scheduled(controller: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
		console.log(`Scheduled job running at ${new Date().toISOString()} with cron: ${controller.cron}`);

		if (controller.cron === '* * * * *') {
			await checkAndSendDueReminders(env);
		}
		if (controller.cron === '*/10 * * * *') {
			await syncUpcomingGames(env, 7);
		}
		if (controller.cron === '0 4 * * *') {
			await periodicMessageSync(env, 48);
		}
	},
} satisfies ExportedHandler<Env>;

async function handleGroupMeWebhook(request: Request, env: Env): Promise<Response> {
	if (request.method !== 'POST') {
		return new Response('Method Not Allowed', { status: 405 });
	}

	let triggerMessage: GroupMeMessage;
	try {
		triggerMessage = await request.json();
		console.log(`${triggerMessage.name.split(' ')[0]}: ${triggerMessage.text}`, triggerMessage);
	} catch {
		return new Response('Bad Request: Invalid JSON', { status: 400 });
	}

	await syncMessageToDb(env, triggerMessage);

	// Process a slash command or chat prompt
	if (triggerMessage.text.startsWith('/')) {
		const args = triggerMessage.text.trim().split(/\s+/);
		const command = args[0].slice(1).toLowerCase();

		const commandHandler = commandRegistry[command];
		if (commandHandler) {
			await commandHandler(env, args, triggerMessage);
		} else {
			await sendMessage(env, triggerMessage.group_id, "That's not a command IDIOT");
		}
	} else if (triggerMessage.text.toLowerCase().includes('meeshbot') && !botUserIds.includes(triggerMessage.user_id)) {
		await respondWithAi(env, triggerMessage);
	}

	return new Response('Success', { status: 200 });
}

async function handleMCPRequest(request: Request, env: Env): Promise<Response> {
	if (request.method !== 'POST') {
		return new Response('Method Not Allowed', { status: 405 });
	}

	let triggerMessage: GroupMeMessage;
	try {
		triggerMessage = await request.json();
		console.log(`${triggerMessage.name.split(' ')[0]}: ${triggerMessage.text}`, triggerMessage);
	} catch {
		return new Response('Bad Request: Invalid JSON', { status: 400 });
	}

	await syncMessageToDb(env, triggerMessage);

	// Process a slash command or chat prompt
	if (triggerMessage.text.startsWith('/')) {
		const args = triggerMessage.text.trim().split(/\s+/);
		const command = args[0].slice(1).toLowerCase();

		const commandHandler = commandRegistry[command];
		if (commandHandler) {
			await commandHandler(env, args, triggerMessage);
		} else {
			await sendMessage(env, triggerMessage.group_id, "That's not a command IDIOT");
		}
	} else if (triggerMessage.text.toLowerCase().includes('@meeshbot') && !botUserIds.includes(triggerMessage.user_id)) {
		await respondWithAi(env, triggerMessage);
	}

	return new Response('Success', { status: 200 });
}
