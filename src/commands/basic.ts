import { Env } from '../index';
import { getMessageCounts } from '../utils/db';
import { helpMessage } from './registry';
import { GroupMeMessage, sendMessage } from '../integrations/groupMe';

export async function ping(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, 'pong');
}

export async function help(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, helpMessage);
}

export async function whatIsSam(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, 'idk sounds like a bitch');
}

export async function whatIsJeff(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, 'Oh, you mean Brad?');
}

export async function roll(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	const rollPattern = /^(\d+)d(\d+)$/i;
	const match = args[1].match(rollPattern);
	if (!match) {
		await sendMessage(env, triggerMessage.group_id, "That's not a valid dice roll format dumb ass");
		return;
	}

	const numDice = parseInt(match[1], 10);
	const numSides = parseInt(match[2], 10);
	if (numDice <= 0 || numSides <= 0) {
		await sendMessage(env, triggerMessage.group_id, 'Are you stupid? The numbers need to be greater than zero');
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

	await sendMessage(env, triggerMessage.group_id, resultMessage);
}

export async function scoreboard(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	const counts = await getMessageCounts(env, triggerMessage.group_id);

	let scoreboardLines: string[] = ['🏆 Message Count Leaderboard 🏆\n'];

	for (let i = 0; i < counts.length; i++) {
		scoreboardLines.push(`${i + 1}. ${counts[i].name}: ${counts[i].count}`);
	}
	const scoreboardString = scoreboardLines.join('\n');

	await sendMessage(env, triggerMessage.group_id, scoreboardString);
}
