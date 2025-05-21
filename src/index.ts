import { GroupMeMessage, sendMessage } from './integrations/groupMe';
import { commandRegistry } from './commands/registry';
import { botUserIds } from './secrets';
import { respondWithAi } from './commands/chat';
import { checkAndSendDueReminders } from './commands/reminders';
import { syncMessageToDb } from './utils/db';

export interface Env {
	DB: D1Database;
	OPENAI_API_KEY: string;
	GROUPME_TOKEN: string;
	ANTHROPIC_API_KEY: string;
}

export interface ScheduledController {
	readonly scheduledTime: number;
	readonly cron: string;
	noRetry(): void;
}

export default {
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		if (request.method !== 'POST') {
			return new Response('Method Not Allowed', { status: 405 });
		}

		let message: GroupMeMessage;
		try {
			message = await request.json();
			console.log(`${message.name.split(' ')[0]}: ${message.text}`, message);
		} catch {
			return new Response('Bad Request: Invalid JSON', { status: 400 });
		}

		await syncMessageToDb(env, message);

		// Process a slash command or chat prompt
		if (message.text.startsWith('/')) {
			const args = message.text.trim().split(/\s+/);
			const command = args[0].slice(1).toLowerCase();

			const commandHandler = commandRegistry[command];
			if (commandHandler) {
				await commandHandler(env, args, message);
			} else {
				await sendMessage(env, message.group_id, "That's not a command IDIOT");
			}
		} else if (message.text.toLowerCase().includes('@meeshbot') && !botUserIds.includes(message.user_id)) {
			await respondWithAi(env, message);
		}

		return new Response('Success', { status: 200 });
	},

	// Handle cron trigger events
	async scheduled(controller: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
		await checkAndSendDueReminders(env);
	},
} satisfies ExportedHandler<Env>;
