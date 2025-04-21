import { Env, WebhookPayload } from '.';
import * as commands from './commands';

export const commandRegistry: {
	[command: string]: (env: Env, args: string[], payload: WebhookPayload) => Promise<void>;
} = {
	ping: commands.ping,
	whatissam: commands.whatissam,
	roll: commands.roll,
};
