import { Env } from '.';
import * as commands from './commands';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], userId: string, userName: string, attachments: unknown[]) => Promise<void>;
} = {
	ping: commands.ping,
	whatissam: commands.whatissam,
	roll: commands.roll,
};
