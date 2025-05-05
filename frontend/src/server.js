const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

// Serve static files from the React app
app.use(express.static(path.join(__dirname, 'build')));

// Proxy API requests to Flask backend
app.use('/api', createProxyMiddleware({
  target: 'https://join-the-siege-nwh2.onrender.com',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '', // Removes the `/api` prefix from requests
  },
}));

// Serve React's index.html for all non-API routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
