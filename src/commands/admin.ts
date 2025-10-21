import { Env } from '../index';
import { syncMessageToDb } from '../utils/db';
import { adminUserIds, botUserIds } from '../secrets';
import { getMessages, GroupMeMessage, sendMessage } from '../integrations/groupMe';
import { Game, getGames, saveGameToDb } from '../integrations/mlb';

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
				await sendMessage(env, triggerMessage.group_id, `/syncmessages ${groupId} ${beforeId} ${total}`);
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
		console.log('Syncing Tigers games');
		await sendMessage(env, triggerMessage.group_id, 'Syncing games...');
	}

	const season = parseInt(args[1] ?? new Date().getFullYear());
	let cursor: string | undefined = args[2] ?? undefined;
	let totalProcessed = parseInt(args[3] ?? 0);
	let games: Game[] = [];

	try {
		[games, cursor] = await getGames(env, cursor, undefined, season);
		for (const game of games) {
			await saveGameToDb(env, game);
			totalProcessed += 1;
		}
		console.log(`Synced ${games.length} games: ${totalProcessed} total`);
	} catch (error) {
		console.error('Error syncing Tigers games:', error);
		sendMessage(env, triggerMessage.group_id, `Failed to sync Tigers games after ${totalProcessed} games`);
	}

	if (cursor) {
		await sendMessage(env, triggerMessage.group_id, `/synctigers ${season} ${cursor} ${totalProcessed}`);
	} else {
		await sendMessage(env, triggerMessage.group_id, `Success - Synced ${totalProcessed} games`);
	}
}
