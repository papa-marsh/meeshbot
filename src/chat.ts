import { Env } from '.';
import { sendMessage } from './utils';
import { OpenAI } from 'openai';
import { staticAIContext } from './secrets';

const DEFAULT_MODEL = 'gpt-4o';

export async function chat(env: Env, message: string, _userId: string, userName: string): Promise<void> {
	let output: string;
	const context = buildContext(message, userName);
	try {
		const response = await getResponse(context, message, env.OPENAI_API_KEY, DEFAULT_MODEL);
		output = response.output_text;
	} catch {
		output = 'Received an invalid response from our robot overlords :(';
	}
	await sendMessage(env.BOT_ID, output);
}

function buildContext(_message: string, userName: string): string {
	const context = staticAIContext + "In case it's relevant (it probably isn't), " + userName + ' sent this message. \n';
	return context;
}

async function getResponse(developerInput: string, userInput: string, apiKey: string, model: string): Promise<OpenAI.Responses.Response> {
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
