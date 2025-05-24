import { Env } from '../index';
import { OpenAI } from 'openai';
import Anthropic from '@anthropic-ai/sdk';

export const CHAT_MODEL = 'gpt-4.1-nano';
export const COMPUTE_MODEL = 'claude-opus-4-20250514';

export async function getOpenAiResponse(
	env: Env,
	developerPrompt: string,
	userPrompt: string,
	model: string = CHAT_MODEL,
): Promise<string | null> {
	try {
		const client = new OpenAI({ apiKey: env.OPENAI_API_KEY });
		const response = await client.responses.create({
			model: model,
			input: [
				{
					role: 'developer',
					content: developerPrompt,
				},
				{
					role: 'user',
					content: userPrompt,
				},
			],
		});
		return response.output_text ?? null;
	} catch (err) {
		console.log('Failed to get a valid response from OpenAI', err);
		return null;
	}
}

export async function getAnthropicResponse(
	env: Env,
	prompt: string,
	model: string = COMPUTE_MODEL,
	max_tokens: number = 1024,
	temperature: number = 0.1,
): Promise<string | null> {
	try {
		const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
		const response = await client.messages.create({
			model: model,
			max_tokens: max_tokens,
			temperature: temperature,
			messages: [{ role: 'user', content: prompt }],
		});

		const contentBlock = response.content[0];
		const resultText = contentBlock.type === 'text' ? contentBlock.text.trim() : null;

		return resultText;
	} catch (err) {
		console.log('Failed to get a valid response from Anthropic', err);
		return null;
	}
}
