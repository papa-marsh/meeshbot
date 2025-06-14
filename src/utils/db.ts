import { Env } from '../index';
import { GroupMeMessage } from '../integrations/groupMe';
import { ChatMessage, MessageCount } from '../integrations/db';

export async function getGroupIds(env: Env): Promise<string[]> {
	const result = await env.DB.prepare(`SELECT id FROM group_chat;`).all<{ id: string }>();
	return result.results.map((row) => row.id);
}

export async function getBotId(env: Env, groupId: string): Promise<string> {
	const result = await env.DB.prepare(
		`SELECT bot_id FROM group_chat 
			WHERE id = ? 
			LIMIT 1;`,
	)
		.bind(groupId)
		.first<{ bot_id: string }>();

	if (!result) {
		throw new Error(`Group not found for id: ${groupId}`);
	}

	return result.bot_id;
}

export interface MessageHistoryFilters {
	groupId?: string;
	userId?: string;
	before?: Date;
	after?: Date;
}

export async function getMessageHistory(env: Env, filters: MessageHistoryFilters = {}): Promise<ChatMessage[]> {
	const conditions: string[] = [];
	const bindings: (string | number)[] = [];

	if (filters.groupId) {
		conditions.push('chat_message.group_id = ?');
		bindings.push(filters.groupId);
	}

	if (filters.userId) {
		conditions.push('chat_message.sender_id = ?');
		bindings.push(filters.userId);
	}

	if (filters.before) {
		conditions.push('chat_message.timestamp < ?');
		bindings.push(filters.before.toISOString().replace('T', ' ').split('.')[0]);
	}

	if (filters.after) {
		conditions.push('chat_message.timestamp > ?');
		bindings.push(filters.after.toISOString().replace('T', ' ').split('.')[0]);
	}

	const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

	const query = `SELECT chat_message.timestamp, user.name, chat_message.text 
		FROM chat_message 
		JOIN user ON chat_message.sender_id = user.id 
		${whereClause}
		ORDER BY chat_message.timestamp ASC;`;

	const { results } = await env.DB.prepare(query)
		.bind(...bindings)
		.all<ChatMessage>();

	return results.map((row) => ({
		...row,
		timestamp: new Date(row.timestamp),
	})) as ChatMessage[];
}

export async function getMessageCounts(env: Env, groupId: string): Promise<MessageCount[]> {
	const { results } = await env.DB.prepare(
		`SELECT user.name, COUNT(chat_message.id) AS count
			FROM chat_message
			JOIN user ON chat_message.sender_id = user.id
			WHERE chat_message.group_id = ?
			GROUP BY user.name
			ORDER BY count DESC;`,
	)
		.bind(groupId)
		.all<MessageCount>();

	return results;
}

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
