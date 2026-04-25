const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

const ws = new WebSocket(WS_URL);
const logs = [];
let msgId = 0;
let enabled = false;

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  
  if (msg.method === 'Console.messageAdded') {
    const text = msg.params.message.text || '';
    if (text.includes('[HC]') || text.includes('[App]') || text.includes('HealthConnect') || text.includes('biometrics') || text.includes('steps') || text.includes('calories') || text.includes('sleep')) {
      logs.push(text);
      console.log(text);
    }
  }
  
  if (msg.id === 2 && !enabled) {
    enabled = true;
    // Trigger loadBiometrics via window object access
    const jsCode = `
      console.log('[HC] Forcing biometrics reload...');
      // Try to find the app instance and trigger load
      const event = new Event('forceBiometricsReload');
      window.dispatchEvent(event);
      // Also try to directly access if loadBiometrics is global
      if (window.loadBiometrics) {
        console.log('[HC] Found global loadBiometrics');
        window.loadBiometrics(true);
      } else {
        console.log('[HC] loadBiometrics not global, searching...');
      }
    `;
    ws.send(JSON.stringify({
      id: ++msgId,
      method: 'Runtime.evaluate',
      params: { expression: jsCode }
    }));
  }
});

ws.on('error', (err) => {
  console.error('WS Error:', err.message);
});

setTimeout(() => {
  ws.close();
  console.log('\n=== CAPTURED LOGS ===');
  logs.forEach(l => console.log(l));
  console.log(`\nTotal: ${logs.length} logs`);
}, 20000);
