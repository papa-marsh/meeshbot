import { chat } from './chat';
import { commandRegistry } from './registry';
import { respondInChat } from './utils';

export interface Env {
	DB: D1Database;
	BOT_ID: string;
	OPENAI_API_KEY: string;
}

export interface GroupMePayload {
	id: string;
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

		let payload: GroupMePayload;
		try {
			payload = await request.json();
			console.log(payload);
		} catch {
			return new Response('Bad Request: Invalid JSON', { status: 400 });
		}

		await updateDB(env, payload);

		if (payload.sender_type && payload.sender_type.toLowerCase() === 'bot') {
			return new Response('Ignoring bot message', { status: 200 });
		}

		if (payload.text.startsWith('/')) {
			const args = payload.text.trim().split(/\s+/);
			const command = args[0].slice(1).toLowerCase();

			const commandHandler = commandRegistry[command];
			if (commandHandler) {
				await commandHandler(env, args, payload);
			} else {
				await respondInChat(env, payload, "That's not a command IDIOT");
			}
		} else if (payload.text.toLowerCase().includes('@meeshbot')) {
			await chat(env, payload.text, payload.user_id, payload.name);
		}

		return new Response('Success', { status: 200 });
	},
} satisfies ExportedHandler<Env>;

async function updateDB(env: Env, payload: GroupMePayload): Promise<void> {
	try {
		const isBot = payload.sender_type.toLowerCase() === 'bot';
		await env.DB.prepare(
			`INSERT INTO user (id, name, avatar_url, is_bot)
				VALUES (?, ?, ?, ?)
				ON CONFLICT(id) DO UPDATE SET
					name = excluded.name,
					avatar_url = excluded.avatar_url,
					is_bot = excluded.is_bot;`,
		)
			.bind(payload.user_id, payload.name, payload.avatar_url, isBot)
			.run();

		await env.DB.prepare(
			`INSERT INTO group_chat (id)
				VALUES (?)
				ON CONFLICT(id) DO NOTHING;`,
		)
			.bind(payload.group_id)
			.run();

		const attachments_json = JSON.stringify(payload.attachments);
		await env.DB.prepare(
			`INSERT INTO chat_message (id, group_id, sender_id, text, attachments) 
				VALUES (?, ?, ?, ?, ?);`,
		)
			.bind(payload.id, payload.group_id, payload.user_id, payload.text, attachments_json)
			.run();

		await env.DB.prepare(
			`INSERT INTO membership (user_id, group_id) 
				VALUES (?, ?);`,
		)
			.bind(payload.user_id, payload.group_id)
			.run();
	} catch (err) {
		console.log(err);
	}
}
