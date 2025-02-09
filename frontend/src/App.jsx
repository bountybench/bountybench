import React, { useState, useEffect, useRef } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { ToastContainer, toast, Slide } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Routes, Route, Navigate } from 'react-router';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { WorkflowLauncher } from './components/WorkflowLauncher/WorkflowLauncher';
import { AppHeader } from './components/AppHeader/AppHeader';
import { darkTheme } from './theme';
import './App.css';
import HomePage from './components/HomePage/HomePage';
import LogViewer from './components/LogViewer/LogViewer';

function App() {
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(true);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const toastIdRef = useRef({});

  const handleWorkflowStart = (workflowId, model, isInteractive) => {
    setSelectedWorkflow({ id: workflowId, model: model });
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

        console.log('Backend updated with new interactive mode:', newInteractiveMode);
      } catch (error) {
        console.error('Error updating interactive mode:', error);
        setInteractiveMode(!newInteractiveMode); // Revert state on error
      }
    }
  };

  const handleModelChange = async (name) => {
    const url = `http://localhost:8000/workflow/model-change/${selectedWorkflow.id}`;
    const requestBody = { new_model_name: name };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response body:', errorText);
      throw new Error(`HTTP error! status: ${response.status}`);
    } 
  };

  const handleWorkflowStateUpdate = (status, phase) => {
    setWorkflowStatus(status);
    setCurrentPhase(phase);
  };

  useEffect(() => {
    const originalConsoleError = console.error;

    console.error = function(...args) {
      const errorMessage = args.join(' ');

      // Check if the toast already exists
      if (toastIdRef.current[errorMessage]) {
        // Update the existing toast with the same message
        toast.update(toastIdRef.current[errorMessage], {
          render: errorMessage,
          autoClose: 3000,
          transition: Slide,
        });
      } else {
        // Create a new toast and store the ID
        const id = toast.error(errorMessage, {
          position: "top-center",
          autoClose: 3000,
          transition: Slide,
        });
        toastIdRef.current[errorMessage] = id;
      }  
      originalConsoleError.apply(console, args);
    };

    return () => {
      console.error = originalConsoleError;
    };
  }, []);
  
  // Error Toast for invalid workflows
  const showInvalidWorkflowToast = () => {
    console.error("Workflow ID not found, returning to main.");
  };
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className='app-container' display='flex' flexDirection='column' height='100vh'>
        <ToastContainer />
        <AppHeader
          onInteractiveModeToggle={handleInteractiveModeToggle}
          interactiveMode={interactiveMode}
          selectedWorkflow={selectedWorkflow}
          workflowStatus={workflowStatus}
          currentPhase={currentPhase}
          onModelChange={handleModelChange}
        />
<<<<<<< HEAD
        <Box flexGrow={1} overflow='auto'>
          <Routes>
            <Route path='/' element={<HomePage/>} />
            <Route path='/create-workflow' element={<WorkflowLauncher onWorkflowStart={handleWorkflowStart} interactiveMode={interactiveMode} setInteractiveMode={setInteractiveMode} />} />
            <Route path='/workflow' element={<Navigate to="/" />} />
            <Route path='/workflow/:workflowId' 
              element={
                <WorkflowDashboard 
                  interactiveMode={interactiveMode} 
                  onWorkflowStateUpdate={handleWorkflowStateUpdate} 
                  showInvalidWorkflowToast={showInvalidWorkflowToast}
                />} 
            />
            <Route path="/history-logs" element={<LogViewer />} />
            {/* Fallback route */}
            <Route path='*' element={<Navigate to="/" />} />
          </Routes>
        </Box>
=======
        <Routes>
          <Route 
            path="/" 
            element={
              selectedWorkflow ? (
                <WorkflowDashboard 
                  selectedWorkflow={selectedWorkflow}
                  interactiveMode={interactiveMode}
                  onWorkflowStateUpdate={handleWorkflowStateUpdate}
                />
              ) : (
                <WorkflowLauncher 
                  onWorkflowStart={handleWorkflowStart}
                  interactiveMode={interactiveMode}
                  setInteractiveMode={setInteractiveMode}
                />
              )
            }
          />
          <Route path="/history-logs" element={<LogViewer />} />
        </Routes>
>>>>>>> b06b1c5a8c72af67c7e70c8ea447f23ddac99a22
      </Box>
    </ThemeProvider>
  );
}

export default App;