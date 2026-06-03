const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const ASSETS = path.join(__dirname, 'assets');
const SVG_SRC = path.join(ASSETS, 'logo.svg');

async function main() {
  const svgRaw = fs.readFileSync(SVG_SRC, 'utf8');
  // Replace currentColor with white for tray icon visibility
  const svg = svgRaw.replace(/currentColor/g, 'white');
  const svgBuf = Buffer.from(svg);
  // Syncing version: 50% opacity via SVG attribute
  const svgSync = Buffer.from(svg.replace('<svg ', '<svg opacity="0.5" '));

  await sharp(svgBuf).resize(16, 16).png().toFile(path.join(ASSETS, 'logo-16.png'));
  console.log('✓ logo-16.png');
  await sharp(svgBuf).resize(32, 32).png().toFile(path.join(ASSETS, 'logo-32.png'));
  console.log('✓ logo-32.png');
  await sharp(svgSync).resize(16, 16).png().toFile(path.join(ASSETS, 'logo-syncing-16.png'));
  console.log('✓ logo-syncing-16.png');
}

main().catch(err => { console.error(err); process.exit(1); });
