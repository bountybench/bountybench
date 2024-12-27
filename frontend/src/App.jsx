import React, { useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { Header } from './components/Header/Header';
import { darkTheme } from './theme';
import './App.css';

function App() {
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(false);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className="app-container">
        <Header 
          onInteractiveModeToggle={() => setInteractiveMode(!interactiveMode)}
          interactiveMode={interactiveMode}
        />
        <WorkflowDashboard 
          selectedWorkflow={selectedWorkflow}
          interactiveMode={interactiveMode}
        />
      </Box>
    </ThemeProvider>
  );
}

export default App;
