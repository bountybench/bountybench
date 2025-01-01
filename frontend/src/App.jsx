import React, { useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { WorkflowLauncher } from './components/WorkflowLauncher/WorkflowLauncher';
import { Header } from './components/Header/Header';
import { darkTheme } from './theme';
import './App.css';

function App() {
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(false);

  const handleWorkflowStart = (workflowId, isInteractive) => {
    setSelectedWorkflow({ id: workflowId });
    setInteractiveMode(isInteractive);
  };

  const handleInteractiveModeToggle = () => {
    setInteractiveMode(!interactiveMode);
    // If a workflow is already running, might need to send an update to the backend here
    if (selectedWorkflow) {
      // TODO: Implement backend update for interactive mode change
      console.log("Update backend with new interactive mode:", !interactiveMode);
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className="app-container">
        <Header 
          onInteractiveModeToggle={handleInteractiveModeToggle}
          interactiveMode={interactiveMode}
        />
        {selectedWorkflow ? (
          <WorkflowDashboard 
            selectedWorkflow={selectedWorkflow}
            interactiveMode={interactiveMode}
          />
        ) : (
          <WorkflowLauncher 
            onWorkflowStart={handleWorkflowStart}
            interactiveMode={interactiveMode}
            setInteractiveMode={setInteractiveMode}
          />
        )}
      </Box>
    </ThemeProvider>
  );
}

export default App;