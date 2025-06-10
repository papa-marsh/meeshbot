import { Env } from '../index';
import { getMessageHistory } from '../utils/db';
import { staticAIContext } from '../secrets';
import { getAnthropicMcpResponse } from '../integrations/ai';
import { easternFormatter } from '../utils/datetime';
import { GroupMeMessage, sendMessage } from '../integrations/groupMe';

export async function respondWithAi(env: Env, message: GroupMeMessage): Promise<void> {
	const firstName = message.name.split(' ')[0];
	const messageHistory = await buildMessageHistory(env, message);
	const text = `${firstName}: ${message.text}\n\n----------${messageHistory}`;

	const response = await getAnthropicMcpResponse(env, staticAIContext, text);
	const responseList = response ?? ['Received an invalid response from the robot overlords :('];

	if (!responseList) {
		await sendMessage(env, message.group_id, 'Something went wrong :(');
		return;
	}

	const output = responseList[responseList.length - 1];
	await sendMessage(env, message.group_id, output);
}

async function buildMessageHistory(env: Env, message: GroupMeMessage): Promise<string> {
	const now = new Date();
	const nowFormatted = easternFormatter.format(now);
	const fortyEightHoursAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000);

	const messageHistory = await getMessageHistory(env, {
		groupId: message.group_id,
		after: fortyEightHoursAgo,
	});

	const messageHistoryString = messageHistory
		.map((row) => {
			const timestamp = easternFormatter.format(new Date(row.timestamp));
			return `[${timestamp}] ${row.name}: ${row.text}`;
		})
		.join('\n');

	const historyIntro = `
		The following is group chat message history over the last 48 hours, included for context. 
		The timestamp of the message to which you're responding is ${nowFormatted}.\n\n`;
	return historyIntro + messageHistoryString;
}
