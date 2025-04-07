import { Env } from '.';
import { sendMessage } from './utils';

export async function invalidCommand(env: Env): Promise<void> {
	await sendMessage(env.BOT_ID, "That's not a command YOU FUCKING IDIOT");
}

export async function ping(env: Env, _args: string[], _userId: string, _userName: string, _attachments: unknown[]): Promise<void> {
	await sendMessage(env.BOT_ID, 'pong');
}

export async function whatissam(env: Env, _args: string[], _userId: string, _userName: string, _attachments: unknown[]): Promise<void> {
	await sendMessage(env.BOT_ID, 'idk sounds like a bitch');
}

export async function roll(env: Env, args: string[], _userId: string, _userName: string, _attachments: unknown[]): Promise<void> {
	const rollPattern = /^(\d+)d(\d+)$/i;
	const match = args[1].match(rollPattern);
	if (!match) {
		await sendMessage(env.BOT_ID, "That's not a valid dice roll format dumb ass");
		return;
	}

	const numDice = parseInt(match[1], 10);
	const numSides = parseInt(match[2], 10);
	if (numDice <= 0 || numSides <= 0) {
		await sendMessage(env.BOT_ID, 'Are you stupid? The numbers need to be greater than zero');
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

	await sendMessage(env.BOT_ID, resultMessage);
}
