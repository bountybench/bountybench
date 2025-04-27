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

import { API_BASE_URL } from './config';

function App() {
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [useMockModel, setUseMockModel] = useState(false); 
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
          const response = await fetch(`${API_BASE_URL}/workflow/${selectedWorkflow.id}/interactive`, {
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


  

  const handleModelChange = async (name, mockModel) => {
    if (!selectedWorkflow) return;
    
    const url = `${API_BASE_URL}/workflow/${selectedWorkflow.id}/model-change`;
    const requestBody = { 
      new_model_name: name,
      use_mock_model: mockModel 
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setUseMockModel(mockModel); // Update state if successful
    } catch (error) {
      console.error('Error updating model:', error);
    }
  };

 
  const handleMockModelToggle = async () => {
    const newMockState = !useMockModel;
    setUseMockModel(newMockState);
  
    if (selectedWorkflow) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/${selectedWorkflow.id}/mock-model`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ use_mock_model: newMockState }),
        });
  
        if (!response.ok) {
          throw new Error('Failed to update mock model setting');
        }
  
        console.log('Mock model updated successfully:', newMockState);
      } catch (error) {
        console.error('Error updating mock model:', error);
        setUseMockModel(!newMockState); // Revert on error
  
        // Dismiss any existing toast with the same error message and show a new one
        if (toastIdRef.current["mockModelError"]) {
          toast.dismiss(toastIdRef.current["mockModelError"]);
        }
  
        toastIdRef.current["mockModelError"] = toast.error("Failed to update mock model setting. Please check API keys.", {
          position: "top-center",
          autoClose: 3000,
          transition: Slide,
        });
      }
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
          onMockModelToggle={handleMockModelToggle} // Pass function
          useMockModel={useMockModel} // Pass state

        />
        <Box flexGrow={1} overflow='auto'>
          <Routes>
            <Route path='/' element={<HomePage/>} />
            <Route path='/create-workflow' element={<WorkflowLauncher onWorkflowStart={handleWorkflowStart} interactiveMode={interactiveMode} setInteractiveMode={setInteractiveMode} useMockModel={useMockModel} setUseMockModel={setUseMockModel}  />} />
            <Route path='/workflow' element={<Navigate to="/" />} />
            <Route path='/workflow/:workflowId' 
              element={
                <WorkflowDashboard 
                  interactiveMode={interactiveMode} 
                  onWorkflowStateUpdate={handleWorkflowStateUpdate} 
                  showInvalidWorkflowToast={showInvalidWorkflowToast}
                  useMockModel={useMockModel} // Pass state
                  setUseMockModel={setUseMockModel} // Pass setter function
                />} 
            />
            <Route path="/history-logs" element={<LogViewer />} />
            {/* Fallback route */}
            <Route path='*' element={<Navigate to="/" />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
