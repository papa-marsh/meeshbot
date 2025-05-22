import { Env } from '../index';
import { syncMessageToDb } from '../utils/db';
import { adminUserIds, botUserIds } from '../secrets';
import { getMessages, GroupMeMessage, sendMessage } from '../integrations/groupMe';
import { getGames, GetGamesParams, saveGameToDb, TIGERS_ID } from '../integrations/mlb';

export async function isAdmin(userId: string): Promise<boolean> {
	if ([...adminUserIds, ...botUserIds].includes(userId)) {
		return true;
	} else return false;
}

export async function syncMessages(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	if (!isAdmin(triggerMessage.user_id)) {
		await sendMessage(env, triggerMessage.group_id, 'no');
		return;
	}

	if (!botUserIds.includes(triggerMessage.user_id)) {
		await sendMessage(env, triggerMessage.group_id, 'Syncing messages...');
	}

	// Example Usage: /syncmessages <groupId> <beforeMessageId?>
	const groupId = args[1] ?? triggerMessage.group_id;
	let beforeId = args[2] ?? null;
	let total: number | string = parseInt(args[3] ?? 0);
	let attempts = 0;
	const maxAttempts = 4;

	try {
		let messages = await getMessages(env, groupId, beforeId ?? null);

		while (messages.length) {
			attempts += 1;
			if (attempts > maxAttempts) {
				await sendMessage(env, triggerMessage.group_id, `/sync ${groupId} ${beforeId} ${total}`);
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
		await sendMessage(env, triggerMessage.group_id, `Success - Synced ${total} messages`);
	} catch (err) {
		console.log('Exception raised while syncing', err);
		await sendMessage(env, triggerMessage.group_id, `Something went wrong after ${total} messages :(`);
	}
}

export async function syncTigers(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	if (!isAdmin(triggerMessage.user_id)) {
		await sendMessage(env, triggerMessage.group_id, 'no');
		return;
	}

	if (!botUserIds.includes(triggerMessage.user_id)) {
		await sendMessage(env, triggerMessage.group_id, 'Syncing games...');
	}

	let total: number | string = parseInt(args[3] ?? 0);
	let filterArg: number | string = args[1];

	let gamesParams: GetGamesParams = {
		team_ids: [TIGERS_ID],
		cursor: args[2] ?? null,
	};

	// Parse filter string. `future` will fetch only future games
	if (filterArg === 'future') {
		gamesParams.dateGEQ = new Date();
	} else {
		filterArg = Number(filterArg ?? 2025);
		gamesParams.seasons = [filterArg];
	}

	try {
		let [games, nextCursor] = await getGames(env, gamesParams);

		if (games.length > 0) {
			for (const gamesTemp of games) {
				const gameDate = new Date(gamesTemp.date);
				gamesTemp.notified = gameDate < new Date();

				await saveGameToDb(env, gamesTemp);
				total += 1;
			}
			console.log(`wrote ${games.length} messages (total: ${total})`);
		}
		if (nextCursor) {
			await sendMessage(env, triggerMessage.group_id, `/synctigers ${filterArg} ${nextCursor} ${total}`);
		} else {
			await sendMessage(env, triggerMessage.group_id, `Success - Synced ${total} games`);
		}
	} catch (err) {
		console.log('Exception raised while syncing', err);
		await sendMessage(env, triggerMessage.group_id, `Something went wrong after ${total} games :(`);
	}
}
