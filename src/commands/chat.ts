import { Env } from '../index';
import { getMessageHistory } from '../utils/db';
import { staticAIContext } from '../secrets';
import { getOpenAiResponse, OPENAI_MODEL } from '../integrations/ai';
import { easternFormatter } from '../utils/datetime';
import { GroupMeMessage, sendMessage } from '../integrations/groupMe';

export async function respondWithAi(env: Env, message: GroupMeMessage): Promise<void> {
	const firstName = message.name.split(' ')[0];
	const text = `${firstName}: ${message.text}`;
	const context = await buildContext(env, message);

	const response = await getOpenAiResponse(env, context, text, OPENAI_MODEL);
	const output = response ?? 'Received an invalid response from the robot overlords :(';

	await sendMessage(env, message.group_id, output);
}

async function buildContext(env: Env, message: GroupMeMessage): Promise<string> {
	const now = easternFormatter.format(new Date());
	const messageHistory = await getMessageHistory(env, message.group_id);
	const messageHistoryString = messageHistory
		.map((row) => {
			const timestamp = easternFormatter.format(new Date(row.timestamp));
			return `[${timestamp}] ${row.name}: ${row.text}`;
		})
		.join('\n');

	const historyIntro = `
		The following is group chat message history, included for context. 
		The timestamp of the message to which you're responding is ${now}.\n\n`;
	const context = staticAIContext + historyIntro + messageHistoryString;
	return context;
}
