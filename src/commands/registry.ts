import { Env } from '../index';
import { GroupMeMessage } from '../integrations/groupMe';
import { reminders, remindme } from './reminders';
import { help, ping, roll, scoreboard, whatissam } from './basic';
import { sync } from './admin';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], payload: GroupMeMessage) => Promise<void>;
} = {
	ping: ping,
	help: help,
	whatissam: whatissam,
	roll: roll,
	scoreboard: scoreboard,
	sync: sync,
	remindme: remindme,
	reminders: reminders,
};

export const helpMessage = `Command List:

/help: Shows this message.

/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice).

/scoreboard: Message count leaderboard.

/remindme: Sets a reminder. Add a custom message with a dash. (eg. "/remindme Friday at noon - Remember the meeting").

/reminders: Shows upcoming reminders.`;
