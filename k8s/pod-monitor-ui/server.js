const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Route for the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Function to get all backend pods
const getBackendPods = () => {
  return new Promise((resolve, reject) => {
    const kubectl = spawn('kubectl', ['get', 'pods', '-o', 'jsonpath={.items[?(@.metadata.labels.app=="backend")].metadata.name}']);
    
    let output = '';
    kubectl.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    kubectl.stderr.on('data', (data) => {
      console.error(`Error: ${data}`);
    });
    
    kubectl.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(`kubectl exited with code ${code}`));
      }
      
      const pods = output.trim().split(/\s+/).filter(Boolean);
      resolve(pods);
    });
  });
};

// Function to get pod status
const getPodStatus = () => {
  return new Promise((resolve, reject) => {
    const kubectl = spawn('kubectl', ['get', 'pods', '-l', 'app=backend', '-o', 'json']);
    
    let output = '';
    kubectl.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    kubectl.stderr.on('data', (data) => {
      console.error(`Error: ${data}`);
    });
    
    kubectl.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(`kubectl exited with code ${code}`));
      }
      
      try {
        const podData = JSON.parse(output);
        resolve(podData);
      } catch (err) {
        reject(err);
      }
    });
  });
};

// Function to get pod details
const getPodDetails = (podName) => {
  return new Promise((resolve, reject) => {
    const kubectl = spawn('kubectl', ['describe', 'pod', podName]);
    
    let output = '';
    kubectl.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    kubectl.stderr.on('data', (data) => {
      console.error(`Error: ${data}`);
    });
    
    kubectl.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(`kubectl exited with code ${code}`));
      }
      
      resolve(output);
    });
  });
};

// Socket.IO connection handling
io.on('connection', async (socket) => {
  console.log('New client connected');
  
  try {
    // Send initial pod list
    const pods = await getBackendPods();
    socket.emit('podList', pods);
    
    // Send initial pod status
    const podStatus = await getPodStatus();
    socket.emit('podStatus', podStatus);
  } catch (error) {
    console.error('Error getting initial pod data:', error);
    socket.emit('error', { message: 'Failed to get pod data. Make sure kubectl is configured correctly.' });
  }
  
  // Handle request for pod details
  socket.on('getPodDetails', async (podName) => {
    try {
      const details = await getPodDetails(podName);
      socket.emit('podDetails', { podName, details });
    } catch (error) {
      console.error(`Error getting details for pod ${podName}:`, error);
      socket.emit('error', { message: `Failed to get details for pod ${podName}` });
    }
  });
  
  // Handle log streaming requests
  socket.on('streamLogs', (podName) => {
    console.log(`Starting log stream for pod: ${podName}`);
    
    // Kill any existing log stream for this socket
    if (socket.logStream) {
      socket.logStream.kill();
    }
    
    // Start a new log stream
    const logStream = spawn('kubectl', ['logs', '-f', podName, '--tail=50']);
    socket.logStream = logStream;
    
    logStream.stdout.on('data', (data) => {
      socket.emit('logData', { podName, data: data.toString() });
    });
    
    logStream.stderr.on('data', (data) => {
      console.error(`Log stream error: ${data}`);
      socket.emit('error', { message: `Error streaming logs: ${data}` });
    });
    
    logStream.on('close', (code) => {
      console.log(`Log stream for ${podName} closed with code ${code}`);
      socket.emit('logStreamClosed', { podName, code });
    });
  });
  
  // Handle stop streaming request
  socket.on('stopStreamLogs', () => {
    if (socket.logStream) {
      console.log('Stopping log stream');
      socket.logStream.kill();
      socket.logStream = null;
    }
  });
  
  // Handle refresh request
  socket.on('refresh', async () => {
    try {
      const pods = await getBackendPods();
      socket.emit('podList', pods);
      
      const podStatus = await getPodStatus();
      socket.emit('podStatus', podStatus);
    } catch (error) {
      console.error('Error refreshing pod data:', error);
      socket.emit('error', { message: 'Failed to refresh pod data' });
    }
  });
  
  // Clean up on disconnect
  socket.on('disconnect', () => {
    console.log('Client disconnected');
    if (socket.logStream) {
      socket.logStream.kill();
      socket.logStream = null;
    }
  });
});

// Start the server
const PORT = process.env.PORT || 2758;
server.listen(PORT, () => {
  console.log(`Pod Monitor UI server running on port ${PORT}`);
  console.log(`Open http://localhost:${PORT} in your browser to access the UI`);
});
