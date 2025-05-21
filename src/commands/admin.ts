import { Env } from '../index';
import { syncMessageToDb } from '../utils/db';
import { adminUserIds, botUserIds } from '../secrets';
import { GroupMeAPIResponse, GroupMeMessage, sendMessage } from '../integrations/groupMe';

async function isAdmin(userId: string): Promise<boolean> {
	if ([...adminUserIds, ...botUserIds].includes(userId)) {
		return true;
	} else return false;
}

export async function sync(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	if (!isAdmin(message.user_id)) {
		await sendMessage(env, message.group_id, 'no');
		return;
	}

	if (!botUserIds.includes(message.user_id)) {
		await sendMessage(env, message.group_id, 'Syncing messages...');
	}

	const groupId = args[1] ?? message.group_id;
	let beforeId = args[2] ?? null;
	let total: number | string = parseInt(args[3] ?? 0);
	let attempts = 0;
	const maxAttempts = 4;

	try {
		let messages = await getMessages(env, groupId, beforeId ?? null);

		while (messages.length) {
			attempts += 1;
			if (attempts > maxAttempts) {
				await sendMessage(env, message.group_id, `/sync ${groupId} ${beforeId} ${total}`);
				return;
			}
			for (const messageTemp of messages) {
				await syncMessageToDb(env, messageTemp);
				beforeId = messageTemp.id;
				total += 1;
			}
			console.log(`wrote ${messages.length} messages (total: ${total})`);
			messages = await getMessages(env, groupId, beforeId);
		}
		await sendMessage(env, message.group_id, `Success - Synced ${total} messages`);
	} catch (err) {
		console.log('Exception raised while syncing', err);
		await sendMessage(env, message.group_id, `Something went wrong after ${total} messages :(`);
	}
}

async function getMessages(env: Env, groupId: string, beforeId: string | null = null): Promise<GroupMeMessage[]> {
	const baseUrl = 'https://api.groupme.com/v3';
	let url = `${baseUrl}/groups/${groupId}/messages?token=${env.GROUPME_TOKEN}&limit=25`;

	if (beforeId !== null) {
		url += `&before_id=${beforeId}`;
	}

	const response = await fetch(url);
	if (response.status === 304) {
		return [];
	}

	if (response.status !== 200) {
		throw new Error(`Received ${response.status}`);
	}

	const json: GroupMeAPIResponse = await response.json();
	const messages: GroupMeMessage[] | null = json.response.messages;

	return messages;
}
