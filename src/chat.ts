import { Env } from '.';
import { sendMessage } from './utils';
import { OpenAI } from 'openai';
import { staticAIContext } from './secrets';

const DEFAULT_MODEL = 'gpt-4o';

export async function chat(env: Env, message: string, _userId: string, userName: string): Promise<void> {
	let output: string;
	const context = buildContext(env, message, userName);
	try {
		const response = await getResponse(env, context, message, env.OPENAI_API_KEY, DEFAULT_MODEL);
		output = response.output_text;
	} catch {
		output = 'Received an invalid response from our robot overlords :(';
	}
	await sendMessage(env, env.BOT_ID, output);
}

function buildContext(_env: Env, _message: string, userName: string): string {
	const context = staticAIContext + "In case it's relevant (it probably isn't), " + userName + ' sent this message. \n';
	return context;
}

async function getResponse(
	env: Env,
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
