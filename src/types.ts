// Environment variables and bindings
export interface Env {
	DB: D1Database;
	OPENAI_API_KEY: string;
	GROUPME_TOKEN: string;
	ANTHROPIC_API_KEY: string;
}

// GroupMe API related types
export interface GroupMeMessage {
	id: string;
	created_at: number;
	sender_type: string;
	text: string;
	user_id: string;
	name: string;
	group_id: string;
	avatar_url: string;
	attachments: unknown[];
}

export type GroupMeAPIResponse = {
	meta: {
		code: number;
	};
	response: {
		count: number;
		messages: GroupMeMessage[];
	};
};

export interface Mention {
	user_id: string;
	index: number;
	length: number;
}

export type ReplyAttachment = {
	type: 'reply';
	reply_id: string;
	base_reply_id: string;
};

export type MentionsAttachment = {
	type: 'mentions';
	user_ids: string[];
	loci: [number, number][];
};

export type MessageAttachment = ReplyAttachment | MentionsAttachment;

// Database models
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
	sent: number;
}

// CloudFlare Worker types
export interface ScheduledController {
	readonly scheduledTime: number;
	readonly cron: string;
	noRetry(): void;
}
