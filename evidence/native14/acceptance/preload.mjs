// TEST only: retain the installed package's accepted MODEL-only preload and add an explicit test adapter.
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
if(process.argv[1]?.endsWith('/experimental/durable/main.ts')){
 const plan=JSON.parse(readFileSync(process.env.N14_ACCEPT_PLAN,'utf8'));
 await import(pathToFileURL(plan.modelPreload).href);
 process.argv.push('--extension',plan.observer); // Real main and real registry loader admit this test instrumentation.
}
