const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

const ws = new WebSocket(WS_URL);
const logs = [];
let msgId = 0;
let step = 0;

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  
  if (msg.method === 'Console.messageAdded') {
    const text = msg.params.message.text || '';
    if (text.includes('[HC]') || text.includes('[App]') || text.includes('HealthConnect') || text.includes('biometrics') || text.includes('steps') || text.includes('calories') || text.includes('sleep') || text.includes('Raw Data') || text.includes('TOTAL')) {
      logs.push(text);
      console.log(text);
    }
  }
  
  if (msg.id === 2) {
    step = 1;
    // Step 1: Dispatch a click event on the sync button or trigger loadBiometrics
    const jsCode = `
      console.log('[HC] Triggering biometrics load via event...');
      // Try to find and click a sync button
      const buttons = Array.from(document.querySelectorAll('button'));
      const syncBtn = buttons.find(b => b.textContent && b.textContent.toLowerCase().includes('sync'));
      if (syncBtn) {
        console.log('[HC] Found sync button, clicking...');
        syncBtn.click();
      } else {
        console.log('[HC] No sync button found, buttons:', buttons.map(b => b.textContent).slice(0,5));
      }
    `;
    ws.send(JSON.stringify({
      id: ++msgId,
      method: 'Runtime.evaluate',
      params: { expression: jsCode }
    }));
  }
  
  // After first evaluate, trigger again with a different approach
  if (msg.id === 3) {
    setTimeout(() => {
      const jsCode2 = `
        console.log('[HC] Trying to trigger biometric refresh...');
        // Look for any element with click handler that might refresh data
        window.location.reload();
      `;
      ws.send(JSON.stringify({
        id: ++msgId,
        method: 'Runtime.evaluate',
        params: { expression: jsCode2 }
      }));
    }, 5000);
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
}, 25000);
