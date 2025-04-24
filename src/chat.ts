import { Env, GroupMePayload } from '.';
import { easternFormatter, getMessageHistory, respondInChat } from './utils';
import { OpenAI } from 'openai';
import { staticAIContext } from './secrets';

const CHAT_MODEL = 'gpt-4.1-nano';

export async function respondWithAi(env: Env, payload: GroupMePayload): Promise<void> {
	const firstName = payload.name.split(' ')[0];
	const message = `${firstName}: ${payload.text}`;
	let output: string;
	const context = await buildContext(env, payload);
	try {
		const response = await getResponse(env, context, message, env.OPENAI_API_KEY, CHAT_MODEL);
		output = response.output_text;
	} catch {
		output = 'Received an invalid response from the robot overlords :(';
	}
	await respondInChat(env, payload, output);
}

async function buildContext(env: Env, payload: GroupMePayload): Promise<string> {
	const now = easternFormatter.format(new Date());
	const messageHistory = await getMessageHistory(env, payload.group_id);
	const messageHistoryString = messageHistory
		.map((row) => {
			const timestamp = easternFormatter.format(new Date(row.timestamp));
			return `[${timestamp}] ${row.name}: ${row.text}`;
		})
		.join('\n');

	const historyIntro = `
		The following is group chat message history, included for context. 
		The timestamp of the message to which you're responding is ${now}.`;
	const context = staticAIContext + historyIntro + messageHistoryString;
	console.log(context);
	return context;
}

async function getResponse(
	_env: Env,
	developerInput: string,
	userInput: string,
	apiKey: string,
	model: string,
): Promise<OpenAI.Responses.Response> {
	const client = new OpenAI({ apiKey: apiKey });
	const response = await client.responses.create({
		model: model,
		input: [
			{
				role: 'developer',
				content: developerInput,
			},
			{
				role: 'user',
				content: userInput,
			},
		],
	});
	return response;
}
