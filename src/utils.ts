export async function sendMessage(botId: string, message: string): Promise<void> {
	const payload = {
		text: message,
		bot_id: botId,
	};

	const url = 'https://api.groupme.com/v3/bots/post';
	const init: RequestInit = {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload),
	};

	try {
		const response = await fetch(url, init);
		if (!response.ok) {
			console.error('Error sending message', await response.text());
		}
	} catch (err) {
		console.error('Exception while sending message:', err);
	}
}
