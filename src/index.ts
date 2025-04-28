import { respondWithAi } from './chat';
import { commandRegistry } from './registry';
import { botUserIds } from './secrets';
import { respondInChat, syncMessageToDb } from './utils';

export interface Env {
	DB: D1Database;
	OPENAI_API_KEY: string;
	GROUPME_TOKEN: string;
}

export interface GroupMeMessage {
	id: string;
	created_at: number;
	sender_type: string;
	text: string;
	user_id: string;
	name: string;
	group_id: string;
	avatar_url: string;
	attachments: unknown[];
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

		if (message.text.startsWith('/')) {
			const args = message.text.trim().split(/\s+/);
			const command = args[0].slice(1).toLowerCase();

			const commandHandler = commandRegistry[command];
			if (commandHandler) {
				await commandHandler(env, args, message);
			} else {
				await respondInChat(env, message, "That's not a command IDIOT");
			}
		} else if (message.text.toLowerCase().includes('@meeshbot') && !botUserIds.includes(message.user_id)) {
			await respondWithAi(env, message);
		}

		return new Response('Success', { status: 200 });
	},
} satisfies ExportedHandler<Env>;
