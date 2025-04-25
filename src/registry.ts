import { Env, GroupMeMessage } from '.';
import * as commands from './commands';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], payload: GroupMeMessage) => Promise<void>;
} = {
	ping: commands.ping,
	whatissam: commands.whatissam,
	roll: commands.roll,
	sync: commands.sync,
};
