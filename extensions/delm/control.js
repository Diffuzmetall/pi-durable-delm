// Lightweight service token for clients using the supported Native host transport.
// Authentication/attachment are the Native host's; an identity is not a bearer token.
import { defineService } from '@earendil-works/chord';
export const HOST_PROTOCOL = 1;
export const DeLMControl = defineService('delm.control');
