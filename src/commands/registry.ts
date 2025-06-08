import { Env } from '../index';
import { GroupMeMessage } from '../integrations/groupMe';
import { reminders, remindMe } from './reminders';
import { help, ping, roll, scoreboard, whatIsSam, whatIsJeff } from './basic';
import { syncMessages, syncTigers } from './admin';
import { mlb } from './sports';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], triggerMessage: GroupMeMessage) => Promise<void>;
} = {
	ping: ping,
	help: help,
	whatissam: whatIsSam,
	whatisjeff: whatIsJeff,
	roll: roll,
	scoreboard: scoreboard,
	syncmessages: syncMessages,
	remindme: remindMe,
	reminders: reminders,
	synctigers: syncTigers,
	mlb: mlb,
};

export const helpMessage = `Command List:

/help: Shows this message.

/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice).

/scoreboard: Message count leaderboard.

/remindme: Sets a reminder. Add a custom message with a dash. (eg. "/remindme Friday at noon - Remember the meeting").

/reminders: Shows upcoming reminders.`;
