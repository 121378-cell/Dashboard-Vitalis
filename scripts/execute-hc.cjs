const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

const ws = new WebSocket(WS_URL);
let msgId = 0;
let step = 0;
const results = [];

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  
  if (msg.method === 'Runtime.executionContextCreated') {
    step++;
    if (step === 1) {
      // Try to access the app's healthConnectService directly
      ws.send(JSON.stringify({
        id: ++msgId,
        method: 'Runtime.evaluate',
        params: {
          expression: `
            (async () => {
              try {
                // Try to find the healthConnectService in the React app
                const reactRoot = document.querySelector('[data-reactroot]') || document.querySelector('#root');
                if (window.healthConnectService) {
                  const data = await window.healthConnectService.readTodayBiometrics();
                  return JSON.stringify(data);
                }
                // Try to find it through React devtools
                const keys = Object.keys(window).filter(k => k.toLowerCase().includes('health') || k.toLowerCase().includes('biometric'));
                return 'Health-related globals: ' + keys.join(', ');
              } catch (e) {
                return 'Error: ' + e.message;
              }
            })()
          `,
          awaitPromise: true
        }
      }));
    }
  }
  
  if (msg.id && msg.result && msg.result.result) {
    console.log('Result:', msg.result.result.value || msg.result.result.description || JSON.stringify(msg.result.result));
    ws.close();
  }
  
  if (msg.error) {
    console.error('Error:', msg.error);
    ws.close();
  }
});

ws.on('error', (err) => {
  console.error('WS Error:', err.message);
});

setTimeout(() => {
  ws.close();
}, 10000);
