import { Tool } from '@modelcontextprotocol/sdk/types.js';
import { Env } from '../index';
import { placeholder } from './tools';

// TODO:
//  - MCP auth
//  - Build message lookup MCP tools
//  - Set up MCP tools for existing commands
//  - Make @meeshbot trigger logic smarter

export const TOOLS: Tool[] = [
	{
		name: 'placeholder',
		description: '...',
		inputSchema: {
			type: 'object',
			properties: {},
			required: [],
		},
	},
];

export default {
	async fetch(request: Request, env: Env, _: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);

		// CORS headers for browser compatibility
		const corsHeaders = {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type, Authorization',
		};

		// Handle preflight requests
		if (request.method === 'OPTIONS') {
			return new Response(null, { status: 204, headers: corsHeaders });
		}

		// Handle health checks
		if (url.pathname === '/mcp/health') {
			return new Response('OK', {
				status: 200,
				headers: corsHeaders,
			});
		}

		// Handle MCP requests
		if (request.method === 'POST' && url.pathname === '/mcp') {
			try {
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				const message = (await request.json()) as any;
				const { method, params, id } = message;

				let result;

				if (method === 'initialize') {
					result = {
						protocolVersion: '2024-11-05',
						capabilities: {
							tools: {},
						},
						serverInfo: {
							name: 'meeshbot-mcp',
							version: '1.0.0',
						},
					};
				} else if (method === 'notifications/initialized') {
					// Handle the initialized notification - this is sent after the initialize handshake
					// For notifications, we don't return a result, just acknowledge receipt
					return new Response('', {
						status: 204, // No Content - notification acknowledged
						headers: corsHeaders,
					});
				} else if (method === 'tools/list') {
					result = { tools: TOOLS };
				} else if (method === 'tools/call') {
					const { name, arguments: args } = params;
					let resultJson;

					switch (name) {
						case 'get_current_date_time':
							resultJson = { 'Current Date & Time': new Date().toLocaleString('sv-SE', { timeZone: 'America/New_York' }) };
							break;
						case 'placeholder':
							resultJson = await placeholder(args);
							break;
						default:
							throw new Error(`Unknown tool: ${name}`);
					}
					result = { content: [{ type: 'text', text: JSON.stringify(resultJson) }] };
				} else {
					throw new Error(`Unknown method: ${method}`);
				}

				const responseJson = JSON.stringify({
					jsonrpc: '2.0',
					id,
					result,
				});
				return new Response(responseJson, {
					status: 200,
					headers: {
						'content-type': 'application/json',
						...corsHeaders,
					},
				});
			} catch (error) {
				return new Response(
					JSON.stringify({
						jsonrpc: '2.0',
						id: null,
						error: {
							code: -32000,
							message: `Error processing request: ${error}`,
						},
					}),
					{
						status: 500,
						headers: {
							'content-type': 'application/json',
							...corsHeaders,
						},
					},
				);
			}
		}

		// Handle SSE endpoint for Server-Sent Events transport
		if (request.method === 'GET' && url.pathname === '/mcp') {
			// Return SSE-compatible response
			return new Response('', {
				status: 200,
				headers: {
					'Content-Type': 'text/event-stream',
					'Cache-Control': 'no-cache',
					Connection: 'keep-alive',
					...corsHeaders,
				},
			});
		}

		// Root endpoint - return server info
		if (url.pathname === '/mcp') {
			return new Response(
				JSON.stringify({
					name: 'meeshbot-mcp',
					version: '1.0.0',
					capabilities: ['tools'],
					endpoints: {
						mcp: '/mcp',
						health: '/mcp/health',
					},
				}),
				{
					status: 200,
					headers: {
						'content-type': 'application/json',
						...corsHeaders,
					},
				},
			);
		}

		return new Response('Meeshbot MCP Server - Send POST requests to /mcp endpoint', {
			status: 200,
			headers: {
				'content-type': 'text/plain',
				...corsHeaders,
			},
		});
	},
};
