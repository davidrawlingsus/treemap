#!/usr/bin/env node
/**
 * Upload client logos to Vercel Blob and update database
 * 
 * This script:
 * 1. Reads logo files from images/viz_header_logos/
 * 2. Uploads each to Vercel Blob
 * 3. Extracts hex color from filename
 * 4. Updates the database via API endpoint
 */

const fs = require('fs');
const path = require('path');
const { put } = require('@vercel/blob');
require('dotenv').config();
const backendEnvPath = path.join(__dirname, 'backend', '.env');
if (fs.existsSync(backendEnvPath)) {
  require('dotenv').config({ path: backendEnvPath, override: false });
}

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const BLOB_TOKEN = process.env.BLOB_READ_WRITE_TOKEN;

if (!BLOB_TOKEN) {
  console.error('❌ BLOB_READ_WRITE_TOKEN not found in environment');
  process.exit(1);
}

// Mapping of logo filenames to client names and hex colors
const CLIENT_LOGO_MAP = {
  'absolute_reg_logo_#F3F3F3.png': { name: 'Absolute Reg', color: '#F3F3F3' },
  'ancient_and_brave_logo_#212121.png': { name: 'Ancient & Brave', color: '#212121' },
  'katkin_logo_#000000.png': { name: 'Katkin', color: '#000000' },
  'liforme_logo_#FFFFFF.png': { name: 'Liforme', color: '#FFFFFF' },
  'martin_randall_travel_logo_#FFFFFF.png': { name: 'Martin Randall Travel', color: '#FFFFFF' },
  'mous_logo_#FFFFFF.png': { name: 'Mous', color: '#FFFFFF' },
  'neom_organics_logo_#FFFFFF.jpg': { name: 'NEOM Organics', color: '#FFFFFF' },
  'omlet_logo_#FFFFFF.png': { name: 'Omlet', color: '#FFFFFF' },
  'prepkitchen_logo_#FFFFFF.png': { name: 'Prep Kitchen', color: '#FFFFFF' },
  'rabbies_logo_#002D5D.png': { name: 'Rabbies', color: '#002D5D' },
  'the_whisky_exchange_#000000.png': { name: 'The Whisky Exchange', color: '#000000' },
  'USFS_Logo_#FFFFFF.png': { name: 'Online Stores', color: '#FFFFFF' },
};

async function getClientByName(clientName) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/clients`);
    if (!response.ok) {
      throw new Error(`Failed to fetch clients: ${response.status}`);
    }
    const clients = await response.json();
    const client = clients.find(c => c.name === clientName);
    return client || null;
  } catch (error) {
    console.error(`Error fetching client ${clientName}:`, error.message);
    return null;
  }
}

async function uploadLogoToBlob(filePath, filename) {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const fileExtension = path.extname(filename);
    const uniqueFilename = `client_logos/${filename}`;
    
    console.log(`  📤 Uploading to Vercel Blob: ${uniqueFilename}`);
    
    const blob = await put(uniqueFilename, fileBuffer, {
      access: 'public',
      contentType: fileExtension === '.jpg' ? 'image/jpeg' : 'image/png',
      token: BLOB_TOKEN,
    });
    
    console.log(`  ✅ Uploaded: ${blob.url}`);
    return blob.url;
  } catch (error) {
    console.error(`  ❌ Error uploading ${filename}:`, error.message);
    return null;
  }
}

async function updateClientLogo(clientId, logoUrl, headerColor) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/logo`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        logo_url: logoUrl,
        header_color: headerColor,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update client: ${response.status}`);
    }
    
    console.log(`  ✅ Database updated`);
    return true;
  } catch (error) {
    console.error(`  ❌ Error updating database:`, error.message);
    return false;
  }
}

async function main() {
  console.log('🚀 Starting client logo upload process...\n');
  
  const logosDir = path.join(__dirname, 'images', 'viz_header_logos');
  
  if (!fs.existsSync(logosDir)) {
    console.error(`❌ Logos directory not found: ${logosDir}`);
    process.exit(1);
  }
  
  let successCount = 0;
  let failureCount = 0;
  
  for (const [filename, info] of Object.entries(CLIENT_LOGO_MAP)) {
    console.log(`\n📋 Processing: ${filename}`);
    console.log(`   Client: ${info.name}`);
    console.log(`   Color: ${info.color}`);
    
    const filePath = path.join(logosDir, filename);
    
    if (!fs.existsSync(filePath)) {
      console.error(`  ❌ File not found: ${filePath}`);
      failureCount++;
      continue;
    }
    
    // Get client from database
    const client = await getClientByName(info.name);
    if (!client) {
      console.error(`  ❌ Client not found in database: ${info.name}`);
      failureCount++;
      continue;
    }
    
    console.log(`  ✅ Found client ID: ${client.id}`);
    
    // Upload logo to Vercel Blob
    const logoUrl = await uploadLogoToBlob(filePath, filename);
    if (!logoUrl) {
      failureCount++;
      continue;
    }
    
    // Update database
    const updated = await updateClientLogo(client.id, logoUrl, info.color);
    if (updated) {
      successCount++;
    } else {
      failureCount++;
    }
  }
  
  console.log('\n' + '='.repeat(50));
  console.log(`✅ Successfully processed: ${successCount}`);
  console.log(`❌ Failed: ${failureCount}`);
  console.log(`📊 Total: ${successCount + failureCount}`);
  console.log('='.repeat(50));
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
