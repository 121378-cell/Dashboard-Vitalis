const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

async function getLogs() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(WS_URL);
    const logs = [];
    let msgId = 0;

    ws.on('open', () => {
      // Enable console logging
      ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
      // Enable runtime
      ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
    });

    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      
      if (msg.method === 'Console.messageAdded') {
        const log = msg.params.message;
        const text = log.text || '';
        if (text.includes('[HC]') || text.includes('[App]') || text.includes('HealthConnect') || text.includes('biometrics') || text.includes('steps') || text.includes('calories')) {
          logs.push(`[${log.level}] ${text}`);
          console.log(`[${log.level}] ${text}`);
        }
      }
      
      // After enabling, trigger a console clear and reload
      if (msg.id === 2) {
        // Execute JavaScript to trigger Health Connect data load
        ws.send(JSON.stringify({
          id: ++msgId,
          method: 'Runtime.evaluate',
          params: {
            expression: `
              if (window.healthConnectService) {
                window.healthConnectService.readTodayBiometrics().then(d => console.log('[HC] Manual read:', JSON.stringify(d)));
              } else {
                console.log('[HC] healthConnectService not found');
              }
            `
          }
        }));
      }
    });

    ws.on('error', (err) => {
      console.error('WebSocket error:', err.message);
      reject(err);
    });

    // Close after 15 seconds
    setTimeout(() => {
      ws.close();
      resolve(logs);
    }, 15000);
  });
}

getLogs().then(logs => {
  console.log('\n=== CAPTURED LOGS ===');
  logs.forEach(l => console.log(l));
  console.log(`\nTotal logs: ${logs.length}`);
}).catch(err => {
  console.error('Failed:', err.message);
});
