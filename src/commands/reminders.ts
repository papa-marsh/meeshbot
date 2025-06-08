import { Env } from '../index';
import { easternFormatter, parseDateTime } from '../utils/datetime';
import { GroupMeMessage, Mention, sendMessage } from '../integrations/groupMe';
import { Reminder } from '../integrations/db';

export async function remindMe(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	if (args.length < 2) {
		await sendMessage(env, triggerMessage.group_id, 'You need to tell me when to remind you, idiot');
		return;
	}

	// Extract the reminder time and message
	const timeText = args.slice(1).join(' ');
	const reminderMessage = timeText.includes(' - ') ? timeText.substring(timeText.indexOf(' - ') + 3).trim() : "Here's your reminder!";
	const timeString = timeText.includes(' - ') ? timeText.split(' - ')[0].trim() : timeText;

	try {
		const remindAtDate = await parseDateTime(env, timeString);
		if (!remindAtDate) {
			await sendMessage(env, triggerMessage.group_id, "I can't figure out when that is... try something simpler");
			return;
		}

		const now = new Date();
		console.log(`Timestamp comparison: now=${now.toISOString()} remindAtDate=${remindAtDate.toISOString()}`);

		// Ensure reminder is in the future
		if (remindAtDate <= now) {
			await sendMessage(env, triggerMessage.group_id, "I can't remind you in the past, stupid");
			return;
		}

		// Store reminder in database
		await env.DB.prepare(
			`INSERT INTO reminder (id, created, eta, group_id, user_id, message, command_message_id)
			VALUES (?, ?, ?, ?, ?, ?, ?);`,
		)
			.bind(
				crypto.randomUUID(),
				now.toISOString().replace('T', ' ').split('.')[0],
				remindAtDate.toISOString().replace('T', ' ').split('.')[0],
				triggerMessage.group_id,
				triggerMessage.user_id,
				reminderMessage,
				triggerMessage.id,
			)
			.run();

		const formattedRemindTime = easternFormatter.format(remindAtDate);
		await sendMessage(env, triggerMessage.group_id, `OK ${triggerMessage.name.split(' ')[0]}, I'll remind you on ${formattedRemindTime}`);
	} catch (err) {
		console.error('Error creating reminder:', err);
		await sendMessage(env, triggerMessage.group_id, 'Something went wrong setting your reminder :(');
	}
}

export async function reminders(env: Env, args: string[], triggerMessage: GroupMeMessage): Promise<void> {
	try {
		// Build and execute the query
		const query = env.DB.prepare(`
			SELECT reminder.*, user.name AS user_name
			FROM reminder
			JOIN user ON reminder.user_id = user.id
			WHERE reminder.sent = 0
		`);
		const { results } = await query.all<Reminder>();

		// No reminders found
		if (results.length === 0) {
			await sendMessage(env, triggerMessage.group_id, 'No reminders scheduled.');
			return;
		}

		// Format the response
		let response: string[] = ['📋 Upcoming Reminders:\n'];

		for (const reminder of results) {
			const remindAt = new Date(reminder.eta.replace(' ', 'T') + 'Z');
			const formattedDate = easternFormatter.format(remindAt);

			const line = `${reminder.user_name}: "${reminder.message}" - ${formattedDate}`;
			response.push(line);
		}

		await sendMessage(env, triggerMessage.group_id, response.join('\n'));
	} catch (err) {
		console.error('Error listing reminders:', err);
		await sendMessage(env, triggerMessage.group_id, 'Error retrieving reminders :(');
	}
}

export async function checkAndSendDueReminders(env: Env): Promise<void> {
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

			// Send the reminder and mark as sent
			await sendMessage(env, reminder.group_id, reminderText, mentions, reminder.command_message_id);
			await env.DB.prepare(`UPDATE reminder SET sent = 1 WHERE id = ?;`).bind(reminder.id).run();

			console.log(`Sent reminder ${reminder.id} to ${reminder.user_name}`);
		}
	} catch (err) {
		console.error('Error checking reminders:', err);
	}
}
