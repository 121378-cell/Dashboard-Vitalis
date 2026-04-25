const WebSocket = require('ws');

const WS_URL = process.argv[2] || 'ws://localhost:9232/devtools/page/2CB95746F289E8E3C410C656459393D43';

const ws = new WebSocket(WS_URL);
let foundFix = false;
let foundLoadBio = false;
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
      if (text.includes('loadBiometrics') || text.includes('Cargando biométricos')) foundLoadBio = true;
    }
  }
  // Despues de habilitar console, intentar forzar la carga
  if (msg.id === 2) {
    setTimeout(() => {
      ws.send(JSON.stringify({
        id: ++msgId,
        method: 'Runtime.evaluate',
        params: {
          expression: "console.log('[HC] Forzando recarga...'); window.location.reload();"
        }
      }));
    }, 5000);
  }
});

setTimeout(() => {
  ws.close();
  console.log('\n=== RESULTADO ===');
  console.log(foundFix ? '✅ FIX ACTIVO' : '❌ FIX NO DETECTADO');
  console.log(foundLoadBio ? '✅ loadBiometrics detectado' : '❌ loadBiometrics NO detectado');
}, 30000);
