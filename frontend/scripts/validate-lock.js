#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const lockPath = path.join(__dirname, '..', 'package-lock.json');
const lock = JSON.parse(fs.readFileSync(lockPath, 'utf8'));

function getMissingIntegrity(packages) {
  return Object.entries(packages)
    .filter(([name, meta]) => name !== '' && !meta.link && meta.version)
    .filter(([, meta]) => !meta.resolved || !meta.integrity)
    .map(([name]) => name);
}

const missingIntegrity = getMissingIntegrity(lock.packages || {});
if (missingIntegrity.length) {
  console.error('Missing resolved/integrity for:', missingIntegrity.slice(0, 10).join(', '));
  console.error(`Total entries missing integrity: ${missingIntegrity.length}`);
  process.exit(1);
}

const sharpEntry = (lock.packages || {})['node_modules/sharp'];
if (!sharpEntry) {
  console.error('sharp entry not found in lockfile');
  process.exit(1);
}

const expectedSharpOptionals = [
  '@img/sharp-darwin-arm64',
  '@img/sharp-darwin-x64',
  '@img/sharp-libvips-darwin-arm64',
  '@img/sharp-libvips-darwin-x64',
  '@img/sharp-libvips-linux-arm',
  '@img/sharp-libvips-linux-arm64',
  '@img/sharp-libvips-linux-s390x',
  '@img/sharp-libvips-linux-x64',
  '@img/sharp-libvips-linuxmusl-arm64',
  '@img/sharp-libvips-linuxmusl-x64',
  '@img/sharp-linux-arm',
  '@img/sharp-linux-arm64',
  '@img/sharp-linux-s390x',
  '@img/sharp-linux-x64',
  '@img/sharp-linuxmusl-arm64',
  '@img/sharp-linuxmusl-x64',
  '@img/sharp-wasm32',
  '@img/sharp-win32-ia32',
  '@img/sharp-win32-x64',
];

const missingSharpOptionals = expectedSharpOptionals.filter(
  (dep) => !sharpEntry.optionalDependencies || !(dep in sharpEntry.optionalDependencies)
);

if (missingSharpOptionals.length) {
  console.error('Missing sharp optional dependencies:', missingSharpOptionals.join(', '));
  process.exit(1);
}

console.log('Lockfile integrity OK and sharp optional dependencies present.');
