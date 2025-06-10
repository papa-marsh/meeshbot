import { Env } from '../index';
import { OpenAI } from 'openai';
import Anthropic from '@anthropic-ai/sdk';

export const OPENAI_MODEL = 'gpt-4.1-nano';
export const ANTHROPIC_MODEL = 'claude-sonnet-4-20250514';
export const ANTHROPIC_COMPUTE_MODEL = 'claude-opus-4-20250514';

interface AnthropicResponse {
	id: string;
	type: 'message';
	role: 'assistant';
	model: string;
	content: { type: string; text?: string }[];
	stop_reason: string | null;
	stop_sequence: string | null;
}

export async function getOpenAiResponse(
	env: Env,
	developerPrompt: string,
	userPrompt: string,
	model: string = OPENAI_MODEL,
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
	context: string,
	model: string = ANTHROPIC_MODEL,
	temperature: number = 0.3,
	max_tokens: number = 1024,
): Promise<string | null> {
	try {
		const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
		const response = await client.messages.create({
			model: model,
			max_tokens: max_tokens,
			temperature: temperature,
			messages: [{ role: 'user', content: prompt }],
			system: context,
		});

		const contentBlock = response.content[0];
		const resultText = contentBlock.type === 'text' ? contentBlock.text.trim() : null;

		return resultText;
	} catch (err) {
		console.log('Failed to get a valid response from Anthropic', err);
		return null;
	}
}

export async function getAnthropicMcpResponse(
	env: Env,
	system: string,
	prompt: string,
	model: string = ANTHROPIC_MODEL,
	temperature: number = 0.3,
	max_tokens: number = 1024,
): Promise<string[] | null> {
	try {
		const client = new Anthropic({
			apiKey: env.ANTHROPIC_API_KEY,
			defaultHeaders: {
				'anthropic-beta': 'mcp-client-2025-04-04',
			},
		});

		const response: AnthropicResponse = await client.messages.create({
			model: model,
			max_tokens: max_tokens,
			temperature: temperature,
			system: system,
			messages: [{ role: 'user', content: prompt }],
			// @ts-expect-error unsupported in SDK for now
			mcp_servers: [
				// {
				// 	type: 'url',
				// 	url: env.MEESHBOT_MCP_SERVER_URL,
				// 	name: 'meeshbot-mcp',
				// 	authorization_token: env.MEESHBOT_MCP_TOKEN,
				// },
				{
					type: 'url',
					url: env.SPORTS_MCP_SERVER_URL,
					name: 'sports-mcp',
					authorization_token: env.SPORTS_MCP_TOKEN,
				},
			],
		});
		let output = [];
		for (const content of response.content) {
			if (content.type === 'text' && content.text) {
				output.push(content.text.trim());
			}
		}
		return output;
	} catch (err) {
		console.log('Failed to get a valid response from Anthropic MCP', err);
		return null;
	}
}

export async function getSportsMcpResponse(
	env: Env,
	system: string,
	prompt: string,
	model: string = ANTHROPIC_MODEL,
	temperature: number = 0.3,
	max_tokens: number = 1024,
): Promise<string[] | null> {
	try {
		const client = new Anthropic({
			apiKey: env.ANTHROPIC_API_KEY,
			defaultHeaders: {
				'anthropic-beta': 'mcp-client-2025-04-04',
			},
		});

		const response: AnthropicResponse = await client.messages.create({
			model: model,
			max_tokens: max_tokens,
			temperature: temperature,
			system: system,
			messages: [{ role: 'user', content: prompt }],
			// @ts-expect-error unsupported in SDK for now
			mcp_servers: [
				{
					type: 'url',
					url: env.SPORTS_MCP_SERVER_URL,
					name: 'sports-mcp',
					authorization_token: env.SPORTS_MCP_TOKEN,
				},
			],
		});
		let output = [];
		for (const content of response.content) {
			if (content.type === 'text' && content.text) {
				output.push(content.text.trim());
			}
		}
		return output;
	} catch (err) {
		console.log('Failed to get a valid response from Anthropic MCP', err);
		return null;
	}
}
