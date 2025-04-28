import { Env, GroupMeMessage } from '.';
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
};

export const helpMessage = `Command List:

/help: Shows this message.
/roll: Rolls any number of any-sided dice (eg. 4d20 rolls four 20-sided dice).
/scoreboard: Message count leaderboard.`;
