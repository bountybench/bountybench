// Connect to the Socket.IO server
const socket = io();

// DOM elements
const podStatusTable = document.getElementById('podStatusTable');
const podTabs = document.getElementById('podTabs');
const podTabContent = document.getElementById('podTabContent');
const refreshBtn = document.getElementById('refreshBtn');
const podTabTemplate = document.getElementById('podTabTemplate');
const podContentTemplate = document.getElementById('podContentTemplate');
const statusTab = document.getElementById('status-tab');
const detailsTab = document.getElementById('details-tab');
const statusPage = document.getElementById('status-page');
const detailsPage = document.getElementById('details-page');

// Active pod tracking
let activePod = null;
let pods = [];
let podStatusData = {};

// Connect to the server
socket.on('connect', () => {
  console.log('Connected to server');
});

// Handle connection errors
socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
  showError('Failed to connect to the server. Please check if the server is running.');
});

// Handle server errors
socket.on('error', (data) => {
  console.error('Server error:', data.message);
  showError(data.message);
});

// Handle pod list updates
socket.on('podList', (podList) => {
  console.log('Received pod list:', podList);
  pods = podList;
  updatePodTabs();
});

// Handle pod status updates
socket.on('podStatus', (data) => {
  console.log('Received pod status:', data);
  podStatusData = data;
  updatePodStatusTable();
});

// Handle pod details
socket.on('podDetails', (data) => {
  console.log(`Received details for pod ${data.podName}`);
  displayPodDetails(data.podName, data.details);
});

// Handle log data
socket.on('logData', (data) => {
  appendLogData(data.podName, data.data);
});

// Handle log stream closed
socket.on('logStreamClosed', (data) => {
  console.log(`Log stream for ${data.podName} closed with code ${data.code}`);
  if (data.code !== 0) {
    appendLogData(data.podName, `\n[Log stream closed with code ${data.code}]`);
  }
});

// Function to update the pod status table
function updatePodStatusTable() {
  if (!podStatusData || !podStatusData.items || podStatusData.items.length === 0) {
    podStatusTable.querySelector('tbody').innerHTML = '<tr><td colspan="7" class="text-center">No backend pods found</td></tr>';
    return;
  }
  
  const tbody = podStatusTable.querySelector('tbody');
  tbody.innerHTML = '';
  
  podStatusData.items.forEach(pod => {
    const row = document.createElement('tr');
    
    // Get container statuses
    const containerStatuses = pod.status.containerStatuses || [];
    const containerStatus = containerStatuses[0] || {};
    const ready = containerStatuses.length > 0 ? 
      `${containerStatuses.filter(cs => cs.ready).length}/${containerStatuses.length}` : 
      '0/0';
    
    // Calculate restarts
    const restarts = containerStatuses.reduce((sum, cs) => sum + cs.restartCount, 0);
    
    // Calculate age
    const creationTimestamp = new Date(pod.metadata.creationTimestamp);
    const now = new Date();
    const ageMs = now - creationTimestamp;
    const ageHours = Math.floor(ageMs / (1000 * 60 * 60));
    const ageMinutes = Math.floor((ageMs % (1000 * 60 * 60)) / (1000 * 60));
    const age = ageHours > 0 ? `${ageHours}h${ageMinutes}m` : `${ageMinutes}m`;
    
    // Determine status and status class
    let status = pod.status.phase;
    let statusClass = 'status-unknown';
    
    if (status === 'Running') {
      statusClass = 'status-running';
    } else if (status === 'Pending') {
      statusClass = 'status-pending';
    } else if (status === 'Failed' || status === 'Error') {
      statusClass = 'status-error';
    }
    
    row.innerHTML = `
      <td><a href="#" class="pod-name-link" data-pod-name="${pod.metadata.name}">${pod.metadata.name}</a></td>
      <td><span class="status-indicator ${statusClass}"></span> ${status}</td>
      <td>${ready}</td>
      <td>${restarts}</td>
      <td>${age}</td>
      <td>${pod.status.podIP || 'N/A'}</td>
      <td>${pod.spec.nodeName || 'N/A'}</td>
    `;
    
    tbody.appendChild(row);
  });
  
  // Add click event listeners to pod name links
  document.querySelectorAll('.pod-name-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const podName = e.target.getAttribute('data-pod-name');
      selectPod(podName);
    });
  });
  
  // Auto-select the first pod if none is selected
  if (!activePod && podStatusData.items.length > 0) {
    const firstPodName = podStatusData.items[0].metadata.name;
    if (pods.includes(firstPodName)) {
      // Don't switch pages, just prepare the tab
      activePod = firstPodName;
      updatePodTabs();
    }
  }
}

// Function to update pod tabs
function updatePodTabs() {
  // Keep existing tabs for pods that still exist
  const existingTabs = Array.from(podTabs.querySelectorAll('[data-pod-name]'))
    .filter(tab => pods.includes(tab.getAttribute('data-pod-name')));
  
  const existingPodNames = existingTabs.map(tab => tab.getAttribute('data-pod-name'));
  
  // Add tabs for new pods
  const newPods = pods.filter(podName => !existingPodNames.includes(podName));
  
  if (pods.length === 0) {
    // No pods available
    podTabs.innerHTML = '';
    const defaultTab = document.createElement('li');
    defaultTab.className = 'nav-item';
    defaultTab.innerHTML = '<a class="nav-link disabled">No pods available</a>';
    podTabs.appendChild(defaultTab);
    
    // Reset tab content
    podTabContent.innerHTML = '';
    const welcomePane = document.createElement('div');
    welcomePane.className = 'tab-pane fade show active';
    welcomePane.id = 'welcome';
    welcomePane.innerHTML = `
      <div class="pod-content">
        <div class="alert alert-warning">
          <h4>No Backend Pods Found</h4>
          <p>No backend pods were found in the Kubernetes cluster. Please check if your backend deployment is running.</p>
        </div>
      </div>
    `;
    podTabContent.appendChild(welcomePane);
    
    return;
  }
  
  // Clear existing tabs if this is the first update
  if (podTabs.querySelector('.nav-link.disabled')) {
    podTabs.innerHTML = '';
  }
  
  // Add tabs for new pods
  newPods.forEach(podName => {
    const tabClone = podTabTemplate.content.cloneNode(true);
    const tabLink = tabClone.querySelector('.nav-link');
    tabLink.textContent = podName;
    tabLink.setAttribute('data-bs-target', `#pod-${podName}`);
    tabLink.setAttribute('data-pod-name', podName);
    tabLink.id = `tab-${podName}`;
    podTabs.appendChild(tabClone);
    
    // Create corresponding tab content
    const contentClone = podContentTemplate.content.cloneNode(true);
    const tabPane = contentClone.querySelector('.tab-pane');
    tabPane.id = `pod-${podName}`;
    tabPane.setAttribute('aria-labelledby', `tab-${podName}`);
    
    // Set data attributes for buttons
    const viewLogsBtn = contentClone.querySelector('.view-logs-btn');
    const viewDetailsBtn = contentClone.querySelector('.view-details-btn');
    const stopLogsBtn = contentClone.querySelector('.stop-logs-btn');
    
    viewLogsBtn.setAttribute('data-pod-name', podName);
    viewDetailsBtn.setAttribute('data-pod-name', podName);
    stopLogsBtn.setAttribute('data-pod-name', podName);
    
    podTabContent.appendChild(contentClone);
    
    // Add event listeners for the buttons
    document.querySelector(`#pod-${podName} .view-logs-btn`).addEventListener('click', () => {
      startLogStream(podName);
    });
    
    document.querySelector(`#pod-${podName} .view-details-btn`).addEventListener('click', () => {
      requestPodDetails(podName);
    });
    
    document.querySelector(`#pod-${podName} .stop-logs-btn`).addEventListener('click', () => {
      stopLogStream(podName);
    });
  });
  
  // Initialize Bootstrap tabs
  const tabLinks = document.querySelectorAll('.nav-link[data-bs-toggle="tab"]');
  tabLinks.forEach(tabLink => {
    tabLink.addEventListener('click', (e) => {
      e.preventDefault();
      
      // Remove active class from all tabs
      document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
      });
      
      // Hide all tab panes
      document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('show', 'active');
      });
      
      // Activate the clicked tab
      e.target.classList.add('active');
      
      // Show the corresponding tab pane
      const targetId = e.target.getAttribute('data-bs-target');
      const targetPane = document.querySelector(targetId);
      targetPane.classList.add('show', 'active');
      
      // Set active pod
      activePod = e.target.getAttribute('data-pod-name');
    });
  });
  
  // If no pod is active but pods exist, select the first one
  if (!activePod && pods.length > 0) {
    selectPod(pods[0]);
  } else if (activePod && pods.includes(activePod)) {
    // Ensure the active pod tab is still selected
    selectPod(activePod);
  }
}

// Function to select a pod and show its tab
function selectPod(podName) {
  if (!pods.includes(podName)) {
    console.warn(`Pod ${podName} not found in the current pod list`);
    return;
  }
  
  activePod = podName;
  
  // Switch to the details page
  switchToPage('details');
  
  // Activate the tab
  const tabLink = document.querySelector(`#tab-${podName}`);
  if (tabLink) {
    // Simulate a click on the tab
    tabLink.click();
  }
}

// Function to request pod details
function requestPodDetails(podName) {
  console.log(`Requesting details for pod ${podName}`);
  
  // Show the details container and hide the logs container
  const tabPane = document.querySelector(`#pod-${podName}`);
  const logContainer = tabPane.querySelector('.log-container');
  const detailsContainer = tabPane.querySelector('.pod-details');
  const stopLogsBtn = tabPane.querySelector('.stop-logs-btn');
  
  logContainer.style.display = 'none';
  detailsContainer.style.display = 'block';
  stopLogsBtn.style.display = 'none';
  
  // Show loading message
  detailsContainer.textContent = 'Loading pod details...';
  
  // Request pod details from the server
  socket.emit('getPodDetails', podName);
}

// Function to display pod details
function displayPodDetails(podName, details) {
  const tabPane = document.querySelector(`#pod-${podName}`);
  if (!tabPane) return;
  
  const detailsContainer = tabPane.querySelector('.pod-details');
  detailsContainer.textContent = details;
}

// Function to start log streaming
function startLogStream(podName) {
  console.log(`Starting log stream for pod ${podName}`);
  
  // Show the logs container and hide the details container
  const tabPane = document.querySelector(`#pod-${podName}`);
  const logContainer = tabPane.querySelector('.log-container');
  const detailsContainer = tabPane.querySelector('.pod-details');
  const stopLogsBtn = tabPane.querySelector('.stop-logs-btn');
  
  logContainer.style.display = 'block';
  detailsContainer.style.display = 'none';
  stopLogsBtn.style.display = 'inline-block';
  
  // Update terminal title with pod name
  const terminalTitle = logContainer.querySelector('.terminal-title');
  terminalTitle.textContent = `${podName} — kubectl logs — 80×24`;
  
  // Clear existing logs
  const terminalContent = logContainer.querySelector('.terminal-content');
  terminalContent.innerHTML = '';
  
  // Add initial message with timestamp
  const timestamp = getCurrentTimestamp();
  const initialLogLine = document.createElement('div');
  initialLogLine.className = 'log-line info';
  initialLogLine.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> Starting log stream for ${podName}...`;
  terminalContent.appendChild(initialLogLine);
  
  // Request log stream from the server
  socket.emit('streamLogs', podName);
}

// Function to stop log streaming
function stopLogStream(podName) {
  console.log(`Stopping log stream for pod ${podName}`);
  
  const tabPane = document.querySelector(`#pod-${podName}`);
  const stopLogsBtn = tabPane.querySelector('.stop-logs-btn');
  stopLogsBtn.style.display = 'none';
  
  // Tell the server to stop streaming
  socket.emit('stopStreamLogs');
  
  // Add a message to the log
  appendLogData(podName, '[Log stream stopped by user]');
}

// Helper function to get current timestamp
function getCurrentTimestamp() {
  const now = new Date();
  return now.toISOString().replace('T', ' ').substr(0, 19);
}

// Helper function to determine log level based on content
function getLogLevel(line) {
  const lowerLine = line.toLowerCase();
  if (lowerLine.includes('error') || lowerLine.includes('fail') || lowerLine.includes('exception')) {
    return 'error';
  } else if (lowerLine.includes('warn')) {
    return 'warning';
  } else if (lowerLine.includes('info') || lowerLine.includes('starting') || lowerLine.includes('started')) {
    return 'info';
  } else if (lowerLine.includes('success') || lowerLine.includes('completed')) {
    return 'success';
  }
  return '';
}

// Function to append log data
function appendLogData(podName, data) {
  const tabPane = document.querySelector(`#pod-${podName}`);
  if (!tabPane) return;
  
  const logContainer = tabPane.querySelector('.log-container');
  const terminalContent = logContainer.querySelector('.terminal-content');
  
  // Split the data into lines and create elements for each line
  const lines = data.split('\n');
  lines.forEach(line => {
    if (line.trim() === '') return;
    
    // Determine log level based on content
    const logLevel = getLogLevel(line);
    
    const logLine = document.createElement('div');
    logLine.className = `log-line ${logLevel}`;
    
    // Add timestamp for system messages
    if (line.startsWith('[') && (line.includes('stream') || line.includes('stopped'))) {
      const timestamp = getCurrentTimestamp();
      logLine.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${line}`;
    } else {
      logLine.textContent = line;
    }
    
    terminalContent.appendChild(logLine);
    
    // Limit number of lines to prevent performance issues (keep last 1000 lines)
    if (terminalContent.children.length > 1000) {
      terminalContent.removeChild(terminalContent.firstChild);
    }
  });
  
  // Auto-scroll to the bottom
  terminalContent.scrollTop = terminalContent.scrollHeight;
}

// Function to show an error message
function showError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'alert alert-danger alert-dismissible fade show';
  errorDiv.innerHTML = `
    <strong>Error:</strong> ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  // Insert after the header
  document.querySelector('.container-fluid').insertBefore(errorDiv, document.querySelector('.main-nav'));
  
  // Auto-dismiss after 10 seconds
  setTimeout(() => {
    errorDiv.remove();
  }, 10000);
}

// Page navigation functions
function switchToPage(pageId) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(page => {
    page.classList.remove('active');
  });
  
  // Remove active class from all main nav links
  document.querySelectorAll('.main-nav .nav-link').forEach(link => {
    link.classList.remove('active');
  });
  
  // Show the selected page
  if (pageId === 'status') {
    statusPage.classList.add('active');
    statusTab.classList.add('active');
  } else if (pageId === 'details') {
    detailsPage.classList.add('active');
    detailsTab.classList.add('active');
  }
}

// Main navigation event listeners
statusTab.addEventListener('click', (e) => {
  e.preventDefault();
  switchToPage('status');
});

detailsTab.addEventListener('click', (e) => {
  e.preventDefault();
  switchToPage('details');
});

// Refresh button click handler
refreshBtn.addEventListener('click', () => {
  console.log('Refreshing pod data');
  socket.emit('refresh');
});

// Initial refresh
socket.emit('refresh');
