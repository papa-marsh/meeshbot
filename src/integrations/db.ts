export type ChatMessage = {
	timestamp: Date;
	name: string;
	text: string;
};

export type MessageCount = {
	name: string;
	count: number;
};

export interface Reminder {
	id: string;
	created: string;
	eta: string;
	group_id: string;
	user_id: string;
	user_name: string;
	message: string;
	command_message_id: string;
	sent: number;
}
