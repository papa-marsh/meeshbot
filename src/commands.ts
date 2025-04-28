import { Env, GroupMeMessage, syncMessageToDb } from '.';
import { getMessageCounts, respondInChat } from './utils';
import { adminUserIds, botUserIds } from './secrets';
import { helpMessage } from './registry';

type GroupMeAPIResponse = {
	meta: {
		code: number;
	};
	response: {
		count: number;
		messages: GroupMeMessage[];
	};
};

export async function ping(env: Env, _args: string[], message: GroupMeMessage): Promise<void> {
	await respondInChat(env, message, 'pong');
}

export async function help(env: Env, _args: string[], message: GroupMeMessage): Promise<void> {
	await respondInChat(env, message, helpMessage);
}

export async function whatissam(env: Env, _args: string[], message: GroupMeMessage): Promise<void> {
	await respondInChat(env, message, 'idk sounds like a bitch');
}

export async function roll(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	const rollPattern = /^(\d+)d(\d+)$/i;
	const match = args[1].match(rollPattern);
	if (!match) {
		await respondInChat(env, message, "That's not a valid dice roll format dumb ass");
		return;
	}

	const numDice = parseInt(match[1], 10);
	const numSides = parseInt(match[2], 10);
	if (numDice <= 0 || numSides <= 0) {
		await respondInChat(env, message, 'Are you stupid? The numbers need to be greater than zero');
		return;
	}

	const rolls: number[] = [];
	let total = 0;
	for (let i = 0; i < numDice; i++) {
		const rollResult = Math.floor(Math.random() * numSides) + 1;
		rolls.push(rollResult);
		total += rollResult;
	}

	const resultMessage = `${numDice}d${numSides} rolled ${total} (${rolls.join(', ')})`;

	await respondInChat(env, message, resultMessage);
}

export async function scoreboard(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	const counts = await getMessageCounts(env, message.group_id);

	let scoreboardLines: string[] = ['🏆 Message Count Leaderboard 🏆\n'];
	// const requesterIndex = counts.findIndex((c) => c.name === message.name);

	for (let i = 0; i < counts.length; i++) {
		// if (i < 3 || i === requesterIndex) {
		scoreboardLines.push(`${i + 1}. ${counts[i].name}: ${counts[i].count}`);
		// }
		// if (i === 4) {
		// 	scoreboardLines.push('...');
		// }
		// if (i >= 4 && i >= requesterIndex) {
		// 	break;
		// }
	}
	const scoreboardString = scoreboardLines.join('\n');

	await respondInChat(env, message, scoreboardString);
}

export async function sync(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	if (![...adminUserIds, ...botUserIds].includes(message.user_id)) {
		await respondInChat(env, message, 'no');
		return;
	}

	if (!botUserIds.includes(message.user_id)) {
		await respondInChat(env, message, 'Syncing messages...');
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
				await respondInChat(env, message, `/sync ${groupId} ${beforeId} ${total}`);
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
		await respondInChat(env, message, `Success - Synced ${total} messages`);
	} catch (err) {
		console.log('Exception raised while syncing', err);
		await respondInChat(env, message, `Something went wrong after ${total} messages :(`);
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
