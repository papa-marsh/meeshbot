import { Env, GroupMeMessage, ChatMessage, MessageCount } from './types';

export async function respondInChat(env: Env, message: GroupMeMessage, text: string): Promise<void> {
	const groupId = message.group_id;
	await sendMessage(env, groupId, text);
}

export async function sendMessage(env: Env, groupId: string, message: string): Promise<void> {
	const payload = {
		text: message,
		bot_id: await getBotId(env, groupId),
	};

	const url = 'https://api.groupme.com/v3/bots/post';
	const init: RequestInit = {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload),
	};

	try {
		const response = await fetch(url, init);
		if (!response.ok) {
			console.error('Error sending message', await response.text());
		}
	} catch (err) {
		console.error('Exception while sending message:', err);
	}
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

export async function getMessageHistory(env: Env, groupId: string): Promise<ChatMessage[]> {
	const { results } = await env.DB.prepare(
		`SELECT chat_message.timestamp, user.name, chat_message.text 
			FROM chat_message 
			JOIN user ON chat_message.sender_id = user.id 
			WHERE chat_message.group_id = ? 
			ORDER BY chat_message.timestamp ASC;`,
	)
		.bind(groupId)
		.all<ChatMessage>();

	return results.map((row) => ({
		...row,
		timestamp: new Date(row.timestamp),
	})) as ChatMessage[];
}

export const easternFormatter = new Intl.DateTimeFormat('en-US', {
	timeZone: 'America/New_York',
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	hour: '2-digit',
	minute: '2-digit',
	hour12: true,
});

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
