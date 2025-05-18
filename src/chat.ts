import { Env, GroupMeMessage } from './types';
import { easternFormatter, getMessageHistory, respondInChat } from './utils';
import { OpenAI } from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { staticAIContext } from './secrets';

const CHAT_MODEL = 'gpt-4.1-nano';
const COMPUTE_MODEL = 'claude-3-opus-20240229';

export async function respondWithAi(env: Env, message: GroupMeMessage): Promise<void> {
	const firstName = message.name.split(' ')[0];
	const text = `${firstName}: ${message.text}`;
	let output: string;
	const context = await buildContext(env, message);
	try {
		const response = await getResponse(env, context, text, env.OPENAI_API_KEY, CHAT_MODEL);
		output = response.output_text;
	} catch {
		output = 'Received an invalid response from the robot overlords :(';
	}
	await respondInChat(env, message, output);
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

async function getResponse(
	_env: Env,
	developerInput: string,
	userInput: string,
	apiKey: string,
	model: string,
): Promise<OpenAI.Responses.Response> {
	try {
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
	} catch (err) {
		console.log('Failed to get an AI response', err);
		throw new Error();
	}
}

export async function parseDateTime(env: Env, timeString: string): Promise<Date | null> {
	const now = new Date();
	const currentTimeString = easternFormatter.format(now);

	const prompt = `
		You are a date/time parser that converts natural language time descriptions into ISO 8601 string format timestamps.

		Current date and time: ${currentTimeString}

		INSTRUCTIONS:
		- You must use the provided "Current date and time" instead of your internal understanding of the current date and time.
		- Parse the following time description: "${timeString}"
		- Assume all provided datetimes are in Eastern Time (America/New_York timezone)
		- Perform the datetime interpretation in eastern time
		- If only a day is given (eg. "tomorrow" or "next tuesday"), then assume the time is 10am Eastern
		- Return ONLY a ISO 8601 string format timestamp for the interpreted time, in the Eastern timezone
		- Do not include any explanations or text
		- If you cannot determine a specific time, return 0
		- The result must be either a valid ISO 8601 string format timestamp or 0 for failure to interpret
		
		Example valid output: 2025-05-17T20:37:00-04:00
		`;
	// - After interpretation, convert the timestamp to UTC, adding hours and accounting for daylight savings as needed

	try {
		const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
		const response = await client.messages.create({
			model: COMPUTE_MODEL,
			max_tokens: 1024,
			temperature: 0.1,
			messages: [{ role: 'user', content: prompt }],
		});

		const contentBlock = response.content[0];
		const resultText = contentBlock.type === 'text' ? contentBlock.text.trim() : null;
		console.log(`currentTimeString=${currentTimeString}`);
		console.log(`Parsing datetime. Received ${resultText} for timeString: "${timeString}"`);
		if (!resultText) return null;

		// Handle the case where AI couldn't determine the time
		if (resultText === '0') return null;

		// Parse the ISO string to a Date object
		const date = new Date(resultText);
		if (date.toString() === 'Invalid Date') return null;

		return date;
	} catch (err) {
		console.error('Error parsing date with AI:', err);
		return null;
	}
}
