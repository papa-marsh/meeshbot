import { Env } from '../index';
import { getBotId, getGroupIds, syncMessageToDb } from '../utils/db';

const BASE_URL = 'https://api.groupme.com/v3';

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

export type GroupMeAPIResponse = {
	meta: {
		code: number;
	};
	response: {
		count: number;
		messages: GroupMeMessage[];
	};
};

export interface Mention {
	user_id: string;
	index: number;
	length: number;
}

export type ReplyAttachment = {
	type: 'reply';
	reply_id: string;
	base_reply_id: string;
};

export type MentionsAttachment = {
	type: 'mentions';
	user_ids: string[];
	loci: [number, number][];
};

export type MessageAttachment = ReplyAttachment | MentionsAttachment;

export async function sendMessage(
	env: Env,
	groupId: string,
	message: string,
	mentions: Mention[] = [],
	replyTo: string | null = null,
): Promise<void> {
	const payload: {
		text: string;
		bot_id: string;
		attachments: MessageAttachment[];
	} = {
		text: message,
		bot_id: await getBotId(env, groupId),
		attachments: [],
	};

	if (replyTo) {
		payload.attachments.push({ type: 'reply', reply_id: replyTo, base_reply_id: replyTo });
	}

	if (mentions.length > 0) {
		const mentionsAttachment: MentionsAttachment = {
			type: 'mentions',
			user_ids: [] as string[],
			loci: [] as [number, number][],
		};
		for (const mention of mentions) {
			mentionsAttachment.user_ids.push(mention.user_id);
			mentionsAttachment.loci.push([mention.index, mention.length]);
		}
		payload.attachments.push(mentionsAttachment);
	}

	const url = `${BASE_URL}/bots/post`;
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

export async function getMessages(env: Env, groupId: string, beforeId: string | null = null): Promise<GroupMeMessage[]> {
	let url = `${BASE_URL}/groups/${groupId}/messages?token=${env.GROUPME_TOKEN}&limit=25`;

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

export async function periodicMessageSync(env: Env, hoursToSync: number): Promise<void> {
	console.log(`Syncing messages from the last ${hoursToSync} hours...`);
	const groupIds = await getGroupIds(env);
	const cutoffTime = new Date(Date.now() - hoursToSync * 60 * 60 * 1000);
	const cutoffTimeString = cutoffTime.toISOString().replace('T', ' ').split('.')[0];

	for (const groupId of groupIds) {
		console.log(`Syncing messages for group: ${groupId}`);
		try {
			// Find the most recent message from before the cutoff time to use as after_id
			const lastOldMessage = await env.DB.prepare(
				`SELECT id FROM chat_message 
				 WHERE group_id = ? AND timestamp < ? 
				 ORDER BY timestamp DESC 
				 LIMIT 1`,
			)
				.bind(groupId, cutoffTimeString)
				.first<{ id: string }>();

			let afterId = lastOldMessage?.id;
			let hasMoreMessages = true;

			// Paginate through all messages after the cutoff
			while (hasMoreMessages) {
				let url = `${BASE_URL}/groups/${groupId}/messages?token=${env.GROUPME_TOKEN}&limit=100&after_id=${afterId}`;

				const response = await fetch(url);

				if (response.status === 304) {
					console.log(`Received 304 status. No more messages.`);
					hasMoreMessages = false;
					continue;
				}

				if (!response.ok) {
					console.error(`Error fetching messages for group ${groupId}:`, response.status);
					break;
				}

				const json: GroupMeAPIResponse = await response.json();
				const messages = json.response.messages;

				if (!messages || messages.length === 0) {
					hasMoreMessages = false;
					continue;
				}

				// Sync messages to database
				console.log(`Syncing ${messages.length} messages`);
				for (const message of messages) {
					await syncMessageToDb(env, message);
				}
				afterId = messages[messages.length - 1].id;
			}
		} catch (error) {
			console.error(`Error syncing messages for group ${groupId}:`, error);
		}
	}
}
