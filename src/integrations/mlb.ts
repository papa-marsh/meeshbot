// https://mlb.balldontlie.io/?javascript#mlb-api

import { Env } from '../index';
import { sendMessage } from './groupMe';

const BASE_URL = 'https://api.balldontlie.io/mlb/v1';
const TIGERS_ID = 10;

interface Team {
	id: number;
	slug: string;
	abbreviation: string;
	display_name: string;
	short_display_name: string;
	name: string;
	location: string;
	league: string;
	division: string;
}

interface TeamData {
	hits: number;
	runs: number;
	errors: number;
	inning_scores: number[];
}

interface ScoringPlay {
	play: string;
	inning: string;
	period: string;
	away_score: number;
	home_score: number;
}

export interface Game {
	id: number;
	home_team_name: string;
	away_team_name: string;
	home_team: Team;
	away_team: Team;
	season: number;
	postseason: boolean;
	date: Date;
	home_team_data: TeamData;
	away_team_data: TeamData;
	venue: string;
	attendance: number;
	conference_play: boolean;
	status: string;
	period: number;
	clock: number;
	display_clock: string;
	scoring_summary: ScoringPlay[];
	notified?: boolean;
}

// interface GameResponse {
// 	data: Game;
// }

interface GamesResponse {
	data: Game[];
	meta: {
		per_page: number;
		next_cursor?: number;
	};
}

// interface MlbGame {
// 	id: number;
// 	status: string;
// 	date: Date;
// 	season: number;
// 	home_team_name: string;
// 	home_team_info: Team;
// 	home_team_stats: TeamData;
// 	away_team_abbr: string;
// 	away_team_info: Team;
// 	away_team_stats: TeamData;
// 	postseason: boolean;
// 	venue: string;
// 	scoring_summary: ScoringPlay[];
// }

// async function getGameById(env: Env, game_id: number): Promise<Game> {
// 	const url = `${BASE_URL}/games/${game_id}`;

// 	const response = await fetch(url, {
// 		headers: {
// 			Authorization: `${env.BALLDONTLIE_API_KEY}`,
// 		},
// 	});

// 	if (!response.ok) {
// 		const errorText = await response.text().catch(() => 'Could not read error response');
// 		throw new Error(`API request failed with status ${response.status}: ${errorText}`);
// 	}

// 	const responseJson: GameResponse = await response.json();
// 	const result = responseJson.data;

// 	// Convert string date to Date object
// 	if (result.date && typeof result.date === 'string') {
// 		result.date = new Date(result.date);
// 	}
// 	return result;
// }

export async function getGames(
	env: Env,
	cursor?: string,
	fromNowUntil?: Date,
	season: number = new Date().getFullYear(),
	teamIds: number[] = [TIGERS_ID],
	pageSize: number = 100,
): Promise<[Game[], string | undefined]> {
	const url = new URL(`${BASE_URL}/games`);

	url.searchParams.append('per_page', pageSize.toString());
	url.searchParams.append('seasons[]', season.toString());
	if (cursor) {
		url.searchParams.append('cursor', cursor);
	}
	if (teamIds) {
		teamIds.forEach((team_id) => {
			url.searchParams.append('team_ids[]', team_id.toString());
		});
	}
	if (fromNowUntil) {
		const iterDate = new Date();
		while (iterDate <= fromNowUntil) {
			url.searchParams.append('dates[]', iterDate.toISOString().split('T')[0]);
			iterDate.setDate(iterDate.getDate() + 1);
		}
	}

	const response = await fetch(url.toString(), {
		headers: {
			Authorization: `${env.BALLDONTLIE_API_KEY}`,
		},
	});

	if (!response.ok) {
		const errorText = await response.text().catch(() => 'Could not read error response');
		throw new Error(`API request failed with status ${response.status}: ${errorText}`);
	}

	const responseJson: GamesResponse = await response.json();
	const result = responseJson.data;
	const nextCursor = responseJson.meta.next_cursor?.toString();

	// Convert string dates to Date objects for all games
	if (result && Array.isArray(result)) {
		result.forEach((game) => {
			if (game.date && typeof game.date === 'string') {
				game.date = new Date(game.date);
			}
		});
	}

	return [result, nextCursor];
}

export async function saveGameToDb(env: Env, game: Game): Promise<void> {
	try {
		// Convert complex objects to JSON strings for storage
		const homeTeamInfo = JSON.stringify(game.home_team);
		const homeTeamStats = JSON.stringify(game.home_team_data);
		const awayTeamInfo = JSON.stringify(game.away_team);
		const awayTeamStats = JSON.stringify(game.away_team_data);
		const scoringSummary = JSON.stringify(game.scoring_summary);
		const notified = game.notified ? game.notified : game.date < new Date();

		// Format date for SQLite
		const dateString =
			game.date instanceof Date
				? game.date.toISOString().replace('T', ' ').split('.')[0]
				: new Date(game.date).toISOString().replace('T', ' ').split('.')[0];

		await env.DB.prepare(
			`INSERT INTO mlb_game (
				id, status, date, season, 
				home_team_abbr, home_team_info, home_team_stats,
				away_team_abbr, away_team_info, away_team_stats,
				postseason, venue, scoring_summary, notified
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(id) DO UPDATE SET
				status = excluded.status,
				date = excluded.date,
				season = excluded.season,
				home_team_abbr = excluded.home_team_abbr,
				home_team_info = excluded.home_team_info,
				home_team_stats = excluded.home_team_stats,
				away_team_abbr = excluded.away_team_abbr,
				away_team_info = excluded.away_team_info,
				away_team_stats = excluded.away_team_stats,
				postseason = excluded.postseason,
				venue = excluded.venue,
				scoring_summary = excluded.scoring_summary;`,
		)
			.bind(
				game.id,
				game.status,
				dateString,
				game.season,
				game.home_team.abbreviation,
				homeTeamInfo,
				homeTeamStats,
				game.away_team.abbreviation,
				awayTeamInfo,
				awayTeamStats,
				game.postseason ? 1 : 0,
				game.venue,
				scoringSummary,
				notified ? 1 : 0,
			)
			.run();
	} catch (err) {
		console.error('Error saving MLB game to database:', err);
		throw err;
	}
}

export async function syncUpcomingGames(env: Env, futureDaysToSync: number = 0): Promise<void> {
	console.log('Syncing Tigers schedule');

	let totalProcessed = 0;
	let games: Game[] = [];
	let cursor: string | undefined = undefined;
	let fromNowUntil = new Date();
	fromNowUntil.setDate(fromNowUntil.getDate() + futureDaysToSync);
	try {
		do {
			[games, cursor] = await getGames(env, cursor, fromNowUntil);
			games.forEach((game) => {
				saveGameToDb(env, game);
				totalProcessed += 1;
			});
		} while (cursor);

		console.log(`Tigers sync completed: ${totalProcessed} games synced`);
	} catch (error) {
		console.error('Failed to sync upcoming Tigers games:', error);
		sendMessage(env, env.TESTING_GROUP_ID, `Failed to sync Tigers games after ${totalProcessed} games`);
	}
}
