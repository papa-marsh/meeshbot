export type ChatMessage = {
	timestamp: Date;
	name: string;
	text: string;
};

export type MessageCount = {
	name: string;
	count: number;
};

export interface User {
	id: string;
	name: string;
	avatar_url: string;
}

export interface GroupChat {
	id: string;
	name: string;
	bot_id: string;
}

export interface Membership {
	user_id: string;
	group_id: string;
}

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

export interface MlbGame {
	id: number;
	status: string;
	date: string;
	season: number;
	home_team_abbr: string;
	home_team_info: string;
	home_team_stats: string;
	away_team_abbr: string;
	away_team_info: string;
	away_team_stats: string;
	postseason: boolean;
	venue: string;
	scoring_summary: string;
	notified: boolean;
}
