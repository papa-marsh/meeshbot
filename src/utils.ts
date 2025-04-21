import { Env, GroupMePayload } from '.';

export async function respondInChat(env: Env, payload: GroupMePayload, message: string): Promise<void> {
	const groupId = payload.group_id;
	await sendMessage(env, groupId, message);
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
	let result = await env.DB.prepare(
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
