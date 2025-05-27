import { Env } from '../index';
import { getSportsMcpResponse } from '../integrations/ai';
import { GroupMeMessage, sendMessage } from '../integrations/groupMe';

export async function mlb(env: Env, _args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	await sendMessage(env, triggerMessage.group_id, 'Let me check...');

	const prompt = triggerMessage.text;
	const responseList = await getSportsMcpResponse(env, prompt);
	console.log('RIGHT HERE', responseList);
	if (!responseList) {
		await sendMessage(env, triggerMessage.group_id, 'Something went wrong :(');
		return;
	}

	const output = responseList[responseList.length - 1];
	await sendMessage(env, triggerMessage.group_id, output);
}
