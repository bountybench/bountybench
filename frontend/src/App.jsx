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
  const [interactiveMode, setInteractiveMode] = useState(true);

  const handleWorkflowStart = (workflowId, isInteractive) => {
    setSelectedWorkflow({ id: workflowId });
    setInteractiveMode(isInteractive);
  };

  const handleInteractiveModeToggle = async () => {
    const newInteractiveMode = !interactiveMode;
    setInteractiveMode(newInteractiveMode);
    
    if (selectedWorkflow) {
      try {
        const response = await fetch(`http://localhost:8000/workflow/${selectedWorkflow.id}/interactive`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ interactive: newInteractiveMode }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to update interactive mode');
        }
        
        console.log("Backend updated with new interactive mode:", newInteractiveMode);
      } catch (error) {
        console.error("Error updating interactive mode:", error);
        setInteractiveMode(!newInteractiveMode);
      }
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