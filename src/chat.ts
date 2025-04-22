import { Env, GroupMePayload } from '.';
import { respondInChat } from './utils';
import { OpenAI } from 'openai';
import { staticAIContext } from './secrets';

const DEFAULT_MODEL = 'gpt-4.1-nano';

export async function respondWithAi(env: Env, payload: GroupMePayload): Promise<void> {
	const message = payload.text;
	let output: string;
	const context = buildContext(env);
	try {
		const response = await getResponse(env, context, message, env.OPENAI_API_KEY, DEFAULT_MODEL);
		output = response.output_text;
	} catch {
		output = 'Received an invalid response from the robot overlords :(';
	}
	await respondInChat(env, payload, output);
}

function buildContext(_env: Env): string {
	const context = staticAIContext;
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
