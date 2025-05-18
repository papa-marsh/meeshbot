import { Env, GroupMeMessage } from './types';
import * as commands from './commands';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], payload: GroupMeMessage) => Promise<void>;
} = {
	ping: commands.ping,
	help: commands.help,
	whatissam: commands.whatissam,
	roll: commands.roll,
	scoreboard: commands.scoreboard,
	sync: commands.sync,
	remindme: commands.remindme,
	reminders: commands.reminders,
};

export const helpMessage = `Command List:

/help: Shows this message.
/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice).
/scoreboard: Message count leaderboard.
/remindme: Sets a reminder for a future time. You can add a custom message with a dash.
    eg. "/remindme Friday at noon - Remember the meeting".
/reminders: Shows upcoming reminders.`;
