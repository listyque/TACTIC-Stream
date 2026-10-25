import clientApi from '../../../../src/pyasm/common/js/client_api.js?raw';
import runtime from '../../../../src/tactic_stream/compatibility/table_action_runtime.js?raw';
import { logRequest, debugLog } from '../debug/debugLog.js';
import { beginActivity, endActivity } from '../../api.js';

// Original synchronous RPC stays in a worker; script UI is returned to existing owners.
export async function runTableScript(
  source,
  context,
  { ticket, signal, confirm, progress }
) {
  const activity = beginActivity(ticket, 'Running…');
  const session = debugLog.sessionId;
  const execute = (confirmation) =>
    new Promise((resolve, reject) => {
      if (signal?.aborted) {
        reject(new DOMException('Table action cancelled', 'AbortError'));
        return;
      }
      const body =
        clientApi +
        '\n' +
        runtime +
        `
self.onmessage = function(event) {
  const context = event.data.context, ticket = event.data.ticket;
  try {
    const result = runTableAction(function(bvr,evt,spt,TacticServerStub,alert,console,window,confirm,document,Option) {
${source}
    }, context, function(method,args,kwargs,project) {
      if (method.startsWith('_') || ['get_ticket','get_ticket_data'].includes(method)) throw new Error('Authentication methods are unavailable in table actions');
      const payload = {method, args:[{ticket,project,language:'python'},...args], kwargs};
      const request = new XMLHttpRequest(), started = performance.now();
      let data, failure;
      try {
        request.open('POST',event.data.url,false);
        request.timeout = 120000;
        request.setRequestHeader('Content-Type','application/json');
        request.send(JSON.stringify(payload));
        data = JSON.parse(request.responseText);
        if (request.status < 200 || request.status >= 300) throw new Error(data.error || 'TACTIC request failed');
        return data.result;
      } catch (error) { failure = error.message; throw error; }
      finally { self.postMessage({type:'rpc',payload,response:data,error:failure,duration:(performance.now()-started)/1000}); }
    },function(title,detail) { self.postMessage({type:'progress',title,detail}); });
    self.postMessage({type:'result',result});
  } catch (error) { self.postMessage({type:'error',error:String(error.message || error),stack:String(error.stack || '')}); }
};`;
      const url = URL.createObjectURL(
        new Blob([body], { type: 'text/javascript' })
      );
      let worker;
      try {
        worker = new Worker(url);
      } catch (error) {
        URL.revokeObjectURL(url);
        reject(error);
        return;
      }
      const finish = (error, result) => {
        clearTimeout(timeout);
        signal?.removeEventListener('abort', abort);
        worker.terminate();
        URL.revokeObjectURL(url);
        error ? reject(error) : resolve(result);
      };
      const abort = () =>
        finish(
          new DOMException(
            'Table action cancelled. Some operations may already have completed.',
            'AbortError'
          )
        );
      const timeout = setTimeout(
        () =>
          finish(
            new Error(
              'Table action timed out. Some operations may already have completed.'
            )
          ),
        120000
      );
      signal?.addEventListener('abort', abort, { once: true });
      worker.onmessage = (event) => {
        const message = event.data;
        if (message.type === 'rpc') {
          if (session === debugLog.sessionId) {
            try {
              logRequest(
                '/admin/rpc',
                message.payload,
                message.response,
                message.error ? new Error(message.error) : null,
                message.duration
              );
            } catch {
              debugLog.storageError =
                'A request could not be recorded in Debug Log.';
            }
          }
        } else if (message.type === 'progress')
          progress?.(message.title, message.detail);
        else if (message.type === 'result') finish(null, message.result);
        else if (message.type === 'error')
          finish(new Error(message.error + '\n' + message.stack));
      };
      worker.onerror = (event) => {
        event.preventDefault();
        finish(new Error(event.message));
      };
      try {
        worker.postMessage({
          ticket,
          url: new URL('/admin/rpc', location.href).href,
          // API records may contain nested Vue proxies; the worker owns JSON data.
          context: JSON.parse(JSON.stringify({ ...context, confirmation }))
        });
      } catch (error) {
        finish(error);
      }
    });
  try {
    let result = await execute(null);
    if (result.confirmation !== undefined) {
      if (result.calls)
        throw new Error(
          'A table action cannot replay API calls for confirmation'
        );
      const accepted = await confirm(result.confirmation);
      if (signal?.aborted)
        throw new DOMException('Table action cancelled', 'AbortError');
      result = await execute({ message: result.confirmation, accepted });
      if (result.confirmation !== undefined)
        throw new Error('Only one confirmation per table action is supported');
    }
    return result;
  } finally {
    endActivity(activity);
  }
}
