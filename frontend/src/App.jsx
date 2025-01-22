import { React, useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { WorkflowLauncher } from './components/WorkflowLauncher/WorkflowLauncher';
import { AppHeader } from './components/AppHeader/AppHeader'; 
import { darkTheme } from './theme';
import './App.css';
import { useWorkflowWebSocket } from './hooks/useWorkflowWebSocket';

function App() {  
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(true);

  const {
    currentPhase,
    workflowStatus,
  } = useWorkflowWebSocket(selectedWorkflow?.id);

  
  const handleWorkflowStart = (workflowId, isInteractive) => {
    setSelectedWorkflow({ id: workflowId });
    setInteractiveMode(isInteractive);
  };

  const handleInteractiveModeToggle = () => {
    setInteractiveMode(!interactiveMode);
    if (selectedWorkflow) {
      console.log("Update backend with new interactive mode:", !interactiveMode);
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className="app-container" display="flex" flexDirection="column" height="100vh">
        <AppHeader 
          onInteractiveModeToggle={handleInteractiveModeToggle}
          interactiveMode={interactiveMode}
          selectedWorkflow={selectedWorkflow}
          workflowStatus={workflowStatus}
          currentPhase={currentPhase}
        />
        <Box flexGrow={1} overflow="auto">
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
      </Box>
    </ThemeProvider>
  );
}

export default App;