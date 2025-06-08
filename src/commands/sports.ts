import { Env } from '../index';
import { getSportsMcpResponse } from '../integrations/ai';
import { GroupMeMessage, sendMessage } from '../integrations/groupMe';

const SPORTS_MCP_INSTRUCTIONS = `You are a helpful sports chatbot for a
GroupMe chat. Provide accurate, fun, and concise responses about sports games,
players, and teams. Keep answers brief but informative, and add some
personality to make responses engaging for a casual chat environment.`;

export async function mlb(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, 'Let me check...');

	const prompt = triggerMessage.text;
	const responseList = await getSportsMcpResponse(env, SPORTS_MCP_INSTRUCTIONS, prompt);
	if (!responseList) {
		await sendMessage(env, triggerMessage.group_id, 'Something went wrong :(');
		return;
	}

	const output = responseList[responseList.length - 1];
	await sendMessage(env, triggerMessage.group_id, output);
}
