const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

const ws = new WebSocket(WS_URL);
const logs = [];
let msgId = 0;

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Console.messageAdded') {
    const text = msg.params.message.text || '';
    if (text.includes('[HC]') || text.includes('[App]') || text.includes('HealthConnect') || text.includes('biometrics') || text.includes('steps') || text.includes('calories') || text.includes('sleep') || text.includes('Raw Data') || text.includes('TOTAL') || text.includes('granted') || text.includes('available')) {
      logs.push(text);
      console.log(text);
    }
  }
  if (msg.id === 2) {
    ws.send(JSON.stringify({
      id: ++msgId,
      method: 'Runtime.evaluate',
      params: {
        expression: `
          console.log('[HC] Triggering manual sync...');
          const buttons = document.querySelectorAll('button, [role="button"]');
          console.log('[HC] Total buttons:', buttons.length);
          for (let btn of buttons) {
            const text = btn.textContent || '';
            if (text.includes('Sincronizar') || text.includes('Sync') || text.includes('Actualizar') || text.includes('Refresh') || text.includes('Recargar')) {
              console.log('[HC] Clicking:', text.substring(0, 50));
              btn.click();
              break;
            }
          }
        `
      }
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
  console.log('Total:', logs.length);
}, 20000);
