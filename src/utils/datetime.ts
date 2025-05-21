import { Env } from '../index';
import { getAnthropicResponse } from '../integrations/ai';

export const easternFormatter = new Intl.DateTimeFormat('en-US', {
	timeZone: 'America/New_York',
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	hour: '2-digit',
	minute: '2-digit',
	hour12: true,
});

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

	try {
		const result = await getAnthropicResponse(env, prompt);
		console.log(`Parsing datetime. Received ${result} for timeString: "${timeString}"`);
		if (!result) return null;

		// Handle the case where AI couldn't determine the time
		if (result === '0') return null;

		// Parse the ISO string to a Date object
		const date = new Date(result);
		if (date.toString() === 'Invalid Date') return null;

		return date;
	} catch (err) {
		console.error('Error parsing date with AI:', err);
		return null;
	}
}
