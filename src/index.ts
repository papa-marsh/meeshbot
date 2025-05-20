import { respondWithAi } from './chat';
import { commandRegistry } from './registry';
import { botUserIds } from './secrets';
import { Env, GroupMeMessage, ScheduledController, Reminder, Mention } from './types';
import { respondInChat, sendMessage, syncMessageToDb } from './utils';

export default {
	// Handle incoming webhook requests
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		if (request.method !== 'POST') {
			return new Response('Method Not Allowed', { status: 405 });
		}

		let message: GroupMeMessage;
		try {
			message = await request.json();
			console.log(`${message.name.split(' ')[0]}: ${message.text}`, message);
		} catch {
			return new Response('Bad Request: Invalid JSON', { status: 400 });
		}

		await syncMessageToDb(env, message);

		// Process a slash command or chat prompt
		if (message.text.startsWith('/')) {
			const args = message.text.trim().split(/\s+/);
			const command = args[0].slice(1).toLowerCase();

			const commandHandler = commandRegistry[command];
			if (commandHandler) {
				await commandHandler(env, args, message);
			} else {
				await respondInChat(env, message, "That's not a command IDIOT");
			}
		} else if (message.text.toLowerCase().includes('@meeshbot') && !botUserIds.includes(message.user_id)) {
			await respondWithAi(env, message);
		}

		return new Response('Success', { status: 200 });
	},

	// Handle cron trigger events
	async scheduled(controller: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
		await checkAndSendDueReminders(env);
	},
} satisfies ExportedHandler<Env>;

async function checkAndSendDueReminders(env: Env): Promise<void> {
	try {
		const now = new Date();
		const nowIsoString = now.toISOString().replace('T', ' ').split('.')[0];

		// Get all reminders that are due and not yet sent
		const { results } = await env.DB.prepare(
			`SELECT reminder.*, user.name AS user_name, user.id AS user_id
			FROM reminder
			JOIN user ON reminder.user_id = user.id
			WHERE reminder.eta <= ?
			AND reminder.sent = 0
			LIMIT 10;`,
		)
			.bind(nowIsoString)
			.all<Reminder>();

		if (results.length) {
			console.log(`Found ${results.length} reminders to send`);
		}

		for (const reminder of results) {
			const name = reminder.user_name.split(' ')[0];
			const reminderText = `🔔 Reminder for ${name}: ${reminder.message}`;
			const mentions: Mention[] = [
				{
					user_id: reminder.user_id,
					index: 16,
					length: name.length,
				},
			];
			// 15, name.length
			// Send the reminder message
			await sendMessage(env, reminder.group_id, reminderText, mentions, reminder.command_message_id);

			// Mark the reminder as sent
			await env.DB.prepare(`UPDATE reminder SET sent = 1 WHERE id = ?;`).bind(reminder.id).run();

			console.log(`Sent reminder ${reminder.id} to ${reminder.user_name}`);
		}
	} catch (err) {
		console.error('Error checking reminders:', err);
	}
}
