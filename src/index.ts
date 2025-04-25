import { respondWithAi } from './chat';
import { commandRegistry } from './registry';
import { respondInChat } from './utils';

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
		} else if (message.text.toLowerCase().includes('@meeshbot')) {
			await respondWithAi(env, message);
		}

		return new Response('Success', { status: 200 });
	},
} satisfies ExportedHandler<Env>;

export async function syncMessageToDb(env: Env, message: GroupMeMessage): Promise<void> {
	try {
		await env.DB.prepare(
			`INSERT INTO user (id, name, avatar_url)
				VALUES (?, ?, ?)
				ON CONFLICT(id) DO UPDATE SET
					name = excluded.name,
					avatar_url = excluded.avatar_url;`,
		)
			.bind(message.user_id, message.name, message.avatar_url)
			.run();

		await env.DB.prepare(
			`INSERT INTO membership (user_id, group_id) 
				VALUES (?, ?)
				ON CONFLICT(user_id, group_id) DO NOTHING;`,
		)
			.bind(message.user_id, message.group_id)
			.run();

		const attachments_json = JSON.stringify(message.attachments);
		const date = new Date(message.created_at * 1000);
		const timestampString = date.toISOString().replace('T', ' ').split('.')[0]; // "YYYY-MM-DD HH:MM:SS"

		await env.DB.prepare(
			`INSERT INTO chat_message (id, group_id, sender_id, text, attachments, timestamp) 
				VALUES (?, ?, ?, ?, ?, ?)
				ON CONFLICT(id) DO NOTHING;`,
		)
			.bind(message.id, message.group_id, message.user_id, message.text, attachments_json, timestampString)
			.run();
	} catch (err) {
		console.log(err);
	}
}
