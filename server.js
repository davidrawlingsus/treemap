const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// API URL will be injected from environment variable
// Default to localhost for development
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

console.log(`🔧 API_BASE_URL: ${API_BASE_URL}`);

// Serve static files from current directory
app.use(express.static(__dirname));

// Also serve common static files explicitly
app.get('/styles.css', (req, res) => {
  res.sendFile(path.join(__dirname, 'styles.css'));
});

app.get('/header.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'header.js'));
});

// Endpoint to get config (so frontend can fetch API URL dynamically)
app.get('/config.js', (req, res) => {
  res.type('application/javascript');
  res.send(`window.APP_CONFIG = { API_BASE_URL: '${API_BASE_URL}' };`);
});

// Support magic-link redirect path (and other SPA routes in the future)
const sendIndex = (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
};

// Serve index.html for root
app.get('/', sendIndex);
app.get('/magic-login', sendIndex);

// Serve client-insights.html
app.get('/client-insights', (req, res) => {
  res.sendFile(path.join(__dirname, 'client-insights.html'));
});

app.get('/client-insights.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'client-insights.html'));
});

app.listen(PORT, () => {
  console.log(`✅ Frontend server running on http://localhost:${PORT}`);
  console.log(`📡 API URL: ${API_BASE_URL}`);
});

