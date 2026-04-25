const WebSocket = require('ws');

const WS_URL = 'ws://localhost:9224/devtools/page/3D4AC512819A5BBD0A289FA396643D43';

const ws = new WebSocket(WS_URL);
let msgId = 0;
let done = false;

ws.on('open', () => {
  ws.send(JSON.stringify({ id: ++msgId, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: ++msgId, method: 'Runtime.enable' }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  
  if (msg.method === 'Console.messageAdded') {
    const text = msg.params.message.text || '';
    if (text.includes('[HC]')) {
      console.log(text);
    }
  }
  
  if (msg.id === 2 && !done) {
    done = true;
    ws.send(JSON.stringify({
      id: ++msgId,
      method: 'Runtime.evaluate',
      params: {
        expression: `
          const buttons = document.querySelectorAll('button, [role="button"], a, .btn, [class*="button"]');
          const texts = Array.from(buttons).map((b, i) => {
            const text = (b.textContent || b.innerText || b.value || '').trim().substring(0, 60);
            return i + ': ' + text + ' (tag=' + b.tagName + ', class=' + b.className.substring(0, 30) + ')';
          }).filter(t => t.length > 4);
          console.log('[HC] All buttons:');
          texts.forEach(t => console.log('[HC]   ' + t));
        `
      }
    }));
    setTimeout(() => ws.close(), 5000);
  }
});

ws.on('error', (err) => {
  console.error('WS Error:', err.message);
});
