const express = require('express');
const path = require('path');
const { put } = require('@vercel/blob');
const multer = require('multer');
const fs = require('fs');

// Load environment variables - try root .env first, then backend/.env
require('dotenv').config(); // Load root .env if it exists
const backendEnvPath = path.join(__dirname, 'backend', '.env');
if (fs.existsSync(backendEnvPath)) {
  require('dotenv').config({ path: backendEnvPath, override: false }); // Load backend/.env, don't override existing vars
  console.log('✅ Loaded environment variables from backend/.env');
} else {
  console.log('⚠️  backend/.env not found');
}

// #region agent log
const rootEnvExists = fs.existsSync(path.join(__dirname, '.env'));
const debugStartupData = {rootEnvExists,backendEnvExists:fs.existsSync(backendEnvPath),blobTokenExists:!!process.env.BLOB_READ_WRITE_TOKEN,blobTokenLength:process.env.BLOB_READ_WRITE_TOKEN?.length||0,cwd:process.cwd(),dirname:__dirname};
fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'server.js:startup',message:'Server startup env check',data:debugStartupData,timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-A,H-C,H-D'})}).catch(()=>{});
// #endregion

const app = express();
const PORT = process.env.PORT || 3000;

// Log blob token status (without exposing the actual token)
if (process.env.BLOB_READ_WRITE_TOKEN) {
  console.log('✅ BLOB_READ_WRITE_TOKEN is configured');
} else {
  console.log('⚠️  BLOB_READ_WRITE_TOKEN is not set');
}

// Enable JSON and file upload parsing
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configure multer for file uploads
const upload = multer({ storage: multer.memoryStorage() });

// API URL will be injected from environment variable
// Default to localhost for development
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

console.log(`🔧 API_BASE_URL: ${API_BASE_URL}`);

// Endpoint to get config (so frontend can fetch API URL dynamically)
// This must be BEFORE express.static so it overrides the static config.js file
app.get('/config.js', (req, res) => {
  res.type('application/javascript');
  res.send(`window.APP_CONFIG = { API_BASE_URL: '${API_BASE_URL}' };`);
});

// API routes must be BEFORE express.static to avoid conflicts
// Media upload endpoint using Vercel Blob SDK
app.post('/api/upload-media', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file provided' });
    }

    const blobToken = process.env.BLOB_READ_WRITE_TOKEN;
    if (!blobToken) {
      console.error('BLOB_READ_WRITE_TOKEN not found in environment variables');
      console.error('Available env vars:', Object.keys(process.env).filter(k => k.includes('BLOB')));
      return res.status(500).json({ error: 'Blob storage not configured' });
    }

    // Generate unique filename
    const fileExtension = req.file.originalname.split('.').pop() || 'bin';
    const uniqueFilename = `insights/${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExtension}`;

    console.log(`Uploading to Vercel Blob: ${uniqueFilename}, size: ${req.file.size} bytes, type: ${req.file.mimetype}`);

    // Upload to Vercel Blob using the SDK
    const blob = await put(uniqueFilename, req.file.buffer, {
      access: 'public',
      contentType: req.file.mimetype,
      token: blobToken,
    });

    console.log(`Upload successful, URL: ${blob.url}`);
    res.json({ url: blob.url });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: error.message || 'Upload failed' });
  }
});

// Ad image upload endpoint using Vercel Blob SDK
app.post('/api/upload-ad-image', upload.single('file'), async (req, res) => {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'server.js:85',message:'upload-ad-image endpoint hit',data:{hasFile:!!req.file,clientId:req.query.client_id||req.body.client_id,blobTokenExists:!!process.env.BLOB_READ_WRITE_TOKEN,blobTokenLength:process.env.BLOB_READ_WRITE_TOKEN?.length||0},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-A,H-B'})}).catch(()=>{});
  // #endregion
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file provided' });
    }

    const blobToken = process.env.BLOB_READ_WRITE_TOKEN;
    if (!blobToken) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'server.js:95',message:'BLOB_READ_WRITE_TOKEN missing',data:{allBlobEnvVars:Object.keys(process.env).filter(k=>k.includes('BLOB')),rootEnvExists:require('fs').existsSync('.env'),backendEnvExists:require('fs').existsSync('./backend/.env')},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-A,H-B,H-C'})}).catch(()=>{});
      // #endregion
      console.error('BLOB_READ_WRITE_TOKEN not found in environment variables');
      return res.status(500).json({ error: 'Blob storage not configured' });
    }

    // Get client_id from query or body
    const clientId = req.query.client_id || req.body.client_id;
    if (!clientId) {
      return res.status(400).json({ error: 'client_id is required' });
    }

    // Generate unique filename with client_id folder
    const fileExtension = req.file.originalname.split('.').pop() || 'bin';
    const uniqueFilename = `ad-images/${clientId}/${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExtension}`;

    console.log(`Uploading ad image to Vercel Blob: ${uniqueFilename}, size: ${req.file.size} bytes, type: ${req.file.mimetype}`);

    // Upload to Vercel Blob using the SDK
    const blob = await put(uniqueFilename, req.file.buffer, {
      access: 'public',
      contentType: req.file.mimetype,
      token: blobToken,
    });

    console.log(`Ad image upload successful, URL: ${blob.url}`);
    res.json({ 
      url: blob.url,
      filename: req.file.originalname,
      file_size: req.file.size,
      content_type: req.file.mimetype
    });
  } catch (error) {
    console.error('Ad image upload error:', error);
    res.status(500).json({ error: error.message || 'Upload failed' });
  }
});

// Serve static files from current directory (AFTER API routes)
// Note: express.static will return 405 (Method Not Allowed) for POST requests to files, not 501
app.use(express.static(__dirname));

// Also serve common static files explicitly
app.get('/styles.css', (req, res) => {
  res.sendFile(path.join(__dirname, 'styles.css'));
});

app.get('/header.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'header.js'));
});

// Support magic-link redirect path (and other SPA routes in the future)
const sendIndex = (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
};

// Serve index.html for root
app.get('/', sendIndex);
app.get('/magic-login', sendIndex);

// client-insights.html removed - using SPA approach in index.html with hash routing

app.listen(PORT, () => {
  console.log(`✅ Frontend server running on http://localhost:${PORT}`);
  console.log(`📡 API URL: ${API_BASE_URL}`);
});

