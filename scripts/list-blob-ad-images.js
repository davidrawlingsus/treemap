/**
 * List ad-images in Vercel Blob and count by client_id.
 * Run from project root: node scripts/list-blob-ad-images.js
 * Requires BLOB_READ_WRITE_TOKEN in .env, backend/.env, or environment.
 * Optional: API_BASE_URL to resolve client names (e.g. Ancient & Brave).
 */
const path = require('path');
require('dotenv').config();
if (!process.env.BLOB_READ_WRITE_TOKEN) {
  require('dotenv').config({ path: path.join(__dirname, '../backend/.env') });
}
const { list } = require('@vercel/blob');

const prefix = 'ad-images/';

async function fetchClientNames() {
  const base = process.env.API_BASE_URL || process.env.BACKEND_URL;
  if (!base) return {};
  try {
    const res = await fetch(`${base.replace(/\/$/, '')}/api/clients`);
    if (!res.ok) return {};
    const clients = await res.json();
    return Object.fromEntries((clients || []).map((c) => [c.id, c.name || c.id]));
  } catch {
    return {};
  }
}

async function main() {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    console.error('BLOB_READ_WRITE_TOKEN not set. Add it to .env or environment.');
    process.exit(1);
  }

  const byClient = {};
  let cursor;
  let total = 0;

  do {
    const result = await list({
      prefix,
      limit: 1000,
      cursor,
      token,
    });
    for (const blob of result.blobs || []) {
      const path = blob.pathname || blob.name || '';
      const after = path.slice(prefix.length);
      const clientId = after.split('/')[0] || 'unknown';
      byClient[clientId] = (byClient[clientId] || 0) + 1;
      total++;
    }
    cursor = result.cursor;
  } while (cursor);

  const nameById = await fetchClientNames();

  console.log('Ad images in Vercel Blob (prefix: ad-images/)\n');
  console.log('By client:');
  const sorted = Object.entries(byClient).sort((a, b) => b[1] - a[1]);
  for (const [clientId, count] of sorted) {
    const label = nameById[clientId] ? `${nameById[clientId]} (${clientId})` : clientId;
    console.log(`  ${label}: ${count}`);
  }
  console.log(`\nTotal: ${total}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
