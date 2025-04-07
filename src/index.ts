import { commandRegistry } from './registry';
import { invalidCommand } from './commands';
import { chat } from './chat';

export interface Env {
	BOT_ID: string;
	OPENAI_API_KEY: string;
}

interface IncomingPayload {
	sender_type?: string;
	text?: string;
	user_id?: string;
	name?: string;
	attachments?: unknown[];
}

export default {
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		if (request.method !== 'POST') {
			return new Response('Method Not Allowed', { status: 405 });
		}

		let payload: IncomingPayload;
		try {
			payload = await request.json();
		} catch {
			return new Response('Bad Request: Invalid JSON', { status: 400 });
		}

		if (payload.sender_type && payload.sender_type.toLowerCase() === 'bot') {
			return new Response('Ignoring bot message', { status: 200 });
		}

		const message = payload.text || '';
		const userId = payload.user_id || '';
		const userName = payload.name || '';
		const attachments = payload.attachments || [];

		console.log(`${userName} sent: ${message}`);

		if (message.startsWith('/')) {
			const args = message.trim().split(/\s+/);
			const command = args[0].slice(1).toLowerCase();

			const commandHandler = commandRegistry[command];
			if (commandHandler) {
				await commandHandler(env, args, userId, userName, attachments);
			} else {
				await invalidCommand(env);
			}
		} else if (message.toLowerCase().includes('@meeshbot')) {
			await chat(env, message, userId, userName);
		}

		return new Response('Success', { status: 200 });
	},
} satisfies ExportedHandler<Env>;
