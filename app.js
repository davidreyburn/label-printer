// BLE UUIDs (reverse-engineered from official Phomemo app)
const SERVICE_UUID = '0000ff00-0000-1000-8000-00805f9b34fb';
const WRITE_UUID   = '0000ff02-0000-1000-8000-00805f9b34fb';
const CHUNK_SIZE   = 128;

const HEADER = new Uint8Array([
  0x1f, 0x11, 0x24, 0x00,  // Phomemo init
  0x1b, 0x40,               // ESC @ reset
  0x1d, 0x76, 0x30, 0x00,  // GS v 0 0 raster image
  0x0c, 0x00,               // width = 12 bytes = 96 px
  0x40, 0x01,               // height = 320 lines
]);
const FOOTER = new Uint8Array([0x1b, 0x64, 0x00]);

const FONT   = "'Consolas', 'Courier New', monospace";
const CW     = 320;  // canvas landscape width (label length)
const CH     = 96;   // canvas landscape height (tape width)
const PAD    = 10;

// --- Label rendering ---

function renderLabel(text) {
  const canvas = document.createElement('canvas');
  canvas.width = CW;
  canvas.height = CH;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, CW, CH);

  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  if (!lines.length) return canvas;

  // Auto-size font to fit all lines
  let fontSize = 8, lineHeight = 10;
  for (let size = 80; size >= 8; size--) {
    ctx.font = `bold ${size}px ${FONT}`;
    const lh = size * 1.2;
    const maxW = Math.max(...lines.map(l => ctx.measureText(l).width));
    const totalH = lines.length * lh;
    if (maxW <= CW - PAD * 2 && totalH <= CH - PAD * 2) {
      fontSize = size;
      lineHeight = lh;
      break;
    }
  }

  ctx.font = `bold ${fontSize}px ${FONT}`;
  ctx.fillStyle = '#000';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const startY = CH / 2 - ((lines.length - 1) * lineHeight) / 2;
  lines.forEach((line, i) => ctx.fillText(line, CW / 2, startY + i * lineHeight));

  return canvas;
}

function canvasToRasterBytes(landscape) {
  // Rotate 90° CCW → printer orientation (96 wide × 320 tall)
  const rot = document.createElement('canvas');
  rot.width = CH;   // 96
  rot.height = CW;  // 320
  const ctx = rot.getContext('2d');
  ctx.translate(0, CW);
  ctx.rotate(-Math.PI / 2);
  ctx.drawImage(landscape, 0, 0);

  const { data } = ctx.getImageData(0, 0, CH, CW);
  const bytes = new Uint8Array(12 * 320);

  for (let y = 0; y < 320; y++) {
    for (let xb = 0; xb < 12; xb++) {
      let byte = 0;
      for (let bit = 0; bit < 8; bit++) {
        const x = xb * 8 + bit;
        const i = (y * 96 + x) * 4;
        const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
        if (brightness < 128) byte |= (1 << (7 - bit));
      }
      bytes[y * 12 + xb] = byte;
    }
  }
  return bytes;
}

// --- BLE ---

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function printLabel(text) {
  if (!navigator.bluetooth) {
    throw new Error('Web Bluetooth not supported. Use Chrome on Android.');
  }

  const device = await navigator.bluetooth.requestDevice({
    filters: [{ name: 'D30' }, { namePrefix: 'Phomemo' }, { namePrefix: 'PHOMEMO' }],
    optionalServices: [SERVICE_UUID],
  });

  const server = await device.gatt.connect();
  const service = await server.getPrimaryService(SERVICE_UUID);
  const char = await service.getCharacteristic(WRITE_UUID);

  const imageBytes = canvasToRasterBytes(renderLabel(text));
  const payload = new Uint8Array(HEADER.length + imageBytes.length + FOOTER.length);
  payload.set(HEADER, 0);
  payload.set(imageBytes, HEADER.length);
  payload.set(FOOTER, HEADER.length + imageBytes.length);

  const write = char.writeValueWithResponse?.bind(char) ?? char.writeValue.bind(char);
  for (let i = 0; i < payload.length; i += CHUNK_SIZE) {
    await write(payload.slice(i, i + CHUNK_SIZE));
    await sleep(10);
  }

  device.gatt.disconnect();
}

// --- UI ---

const input     = document.getElementById('text-input');
const printBtn  = document.getElementById('print-btn');
const statusEl  = document.getElementById('status');
const preview   = document.getElementById('preview');

function updatePreview() {
  const ctx = preview.getContext('2d');
  const text = input.value.trim();
  if (!text) {
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, CW, CH);
    ctx.fillStyle = '#bbb';
    ctx.font = `14px ${FONT}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('preview', CW / 2, CH / 2);
    return;
  }
  ctx.drawImage(renderLabel(text), 0, 0);
}

function setStatus(msg, type = '') {
  statusEl.textContent = msg;
  statusEl.className = type;
}

async function doPrint() {
  const text = input.value.trim();
  if (!text) return;

  printBtn.disabled = true;
  setStatus('Connecting…');
  try {
    await printLabel(text);
    setStatus('Printed!', 'ok');
  } catch (err) {
    if (err.name === 'NotFoundError') setStatus('Cancelled.', 'err');
    else setStatus(err.message, 'err');
  } finally {
    printBtn.disabled = false;
  }
}

input.addEventListener('input', updatePreview);
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doPrint(); }
});
printBtn.addEventListener('click', doPrint);

updatePreview();

// PWA service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js');
}
