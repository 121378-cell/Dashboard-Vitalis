const WebSocket = require('ws');

const WS_URL = process.argv[2];
if (!WS_URL) {
  console.error('Uso: node force-biometrics.cjs <ws-url>');
  process.exit(1);
}

const ws = new WebSocket(WS_URL);
let foundFix = false;
let foundData = false;
let msgId = 0;

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Console.messageAdded') {
    const text = msg.params.message.text || '';
    if (text.includes('[HC]') || text.includes('[App]')) {
      console.log(text);
      if (text.includes('FIX ACTIVO')) foundFix = true;
      if (text.includes('Steps agg') || text.includes('Calories agg') || text.includes('TOTAL')) foundData = true;
    }
  }
  // Tras habilitar console, forzar carga de biométricos
  if (msg.id === 2) {
    setTimeout(() => {
      ws.send(JSON.stringify({
        id: ++msgId,
        method: 'Runtime.evaluate',
        params: {
          expression: "if (typeof loadBiometrics === 'function') { console.log('[App] Forzando loadBiometrics...'); loadBiometrics(true); } else { console.log('[App] loadBiometrics no encontrado'); }"
        }
      }));
    }, 3000);
  }
});

setTimeout(() => {
  ws.close();
  console.log('\n=== RESULTADO ===');
  console.log(foundFix ? '✅ FIX ACTIVO' : '❌ FIX NO DETECTADO');
  console.log(foundData ? '✅ DATOS LEIDOS' : '❌ SIN DATOS');
}, 30000);
