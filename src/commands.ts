import { Env, GroupMeMessage, GroupMeAPIResponse, Reminder } from './types';
import { easternFormatter, getMessageCounts, respondInChat, syncMessageToDb } from './utils';
import { adminUserIds, botUserIds } from './secrets';
import { helpMessage } from './registry';
import { parseDateTime } from './chat';

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

	for (let i = 0; i < counts.length; i++) {
		scoreboardLines.push(`${i + 1}. ${counts[i].name}: ${counts[i].count}`);
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

export async function remindme(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	if (args.length < 2) {
		await respondInChat(env, message, 'You need to tell me when to remind you, idiot');
		return;
	}

	// Extract the reminder time and message
	const timeText = args.slice(1).join(' ');
	const reminderMessage = timeText.includes(' - ') ? timeText.substring(timeText.indexOf(' - ') + 3).trim() : "Here's your reminder!";
	const timeString = timeText.includes(' - ') ? timeText.split(' - ')[0].trim() : timeText;

	try {
		const remindAtDate = await parseDateTime(env, timeString);
		if (!remindAtDate) {
			await respondInChat(env, message, "I can't figure out when that is... try something simpler");
			return;
		}

		const now = new Date();
		console.log(`Timestamp comparison: now=${now.toISOString()} remindAtDate=${remindAtDate.toISOString()}`);

		// Ensure reminder is in the future
		if (remindAtDate <= now) {
			await respondInChat(env, message, "I can't remind you in the past, stupid");
			return;
		}

		// Store reminder in database
		await env.DB.prepare(
			`INSERT INTO reminder (id, created, eta, group_id, user_id, message)
			VALUES (?, ?, ?, ?, ?, ?);`,
		)
			.bind(
				crypto.randomUUID(),
				now.toISOString().replace('T', ' ').split('.')[0],
				remindAtDate.toISOString().replace('T', ' ').split('.')[0],
				message.group_id,
				message.user_id,
				reminderMessage,
			)
			.run();

		const formattedRemindTime = easternFormatter.format(remindAtDate);
		await respondInChat(env, message, `OK ${message.name.split(' ')[0]}, I'll remind you on ${formattedRemindTime}`);
	} catch (err) {
		console.error('Error creating reminder:', err);
		await respondInChat(env, message, 'Something went wrong setting your reminder :(');
	}
}

export async function reminders(env: Env, args: string[], message: GroupMeMessage): Promise<void> {
	try {
		// Build and execute the query
		const query = env.DB.prepare(`
			SELECT reminder.*, user.name AS user_name
			FROM reminder
			JOIN user ON reminder.user_id = user.id
			WHERE reminder.sent = 0
		`);
		const { results } = await query.all<Reminder>();

		// No reminders found
		if (results.length === 0) {
			await respondInChat(env, message, 'No reminders scheduled.');
			return;
		}

		// Format the response
		let response: string[] = ['📋 Upcoming Reminders:\n'];

		for (const reminder of results) {
			const remindAt = new Date(reminder.eta.replace(' ', 'T') + 'Z');
			const formattedDate = easternFormatter.format(remindAt);

			const line = `${reminder.user_name}: "${reminder.message}" - ${formattedDate}`;
			response.push(line);
		}

		await respondInChat(env, message, response.join('\n'));
	} catch (err) {
		console.error('Error listing reminders:', err);
		await respondInChat(env, message, 'Error retrieving reminders :(');
	}
}
