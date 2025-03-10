import React, { useState, useEffect, useRef } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { ToastContainer, toast, Slide } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Routes, Route, Navigate } from 'react-router';
import { WorkflowDashboard } from './components/WorkflowDashboard/WorkflowDashboard';
import { WorkflowLauncher } from './components/WorkflowLauncher/WorkflowLauncher';
import { darkTheme } from './theme';
import './App.css';
import HomePage from './components/HomePage/HomePage';
import LogViewer from './components/LogViewer/LogViewer';

function App() {
  const [workflowSettings, setWorkflowSettings] = useState({});
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);

  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  
  const toastIdRef = useRef({});

  const handleWorkflowStart = (workflowId, model, isInteractive, isMock) => {
    console.log("=============handleWorkflowStart:=============", { workflowId, model, isInteractive, isMock });
    
    // Store settings first before changing selectedWorkflow
    setWorkflowSettings(prev => {
      const newSettings = {
        ...prev,
        [workflowId]: {
          interactiveMode: isInteractive,
          useMockModel: isMock,
        },
      };
      console.log(`Setting workflow ${workflowId} settings:`, newSettings);
      return newSettings;
    });
    
    setSelectedWorkflow({ id: workflowId, model: model });
  };

  // Called by WorkflowDashboard when the workflow’s status changes
  const handleWorkflowStateUpdate = (status, phase) => {
    setWorkflowStatus(status);
    setCurrentPhase(phase);
  };

  // Called by WorkflowDashboard to update either interactiveMode or useMockModel
  const handleUpdateWorkflowSettings = (workflowId, newSettings) => {
    setWorkflowSettings(prev => ({
      ...prev,
      [workflowId]: {
        // Keep prior fields, only override what’s changed
        ...(prev[workflowId] || {}),
        ...newSettings,
      },
    }));
  };

  /**
   * Global error toast logic
   */
  useEffect(() => {
    const originalConsoleError = console.error;
    console.error = function(...args) {
      const errorMessage = args.join(' ');
      if (toastIdRef.current[errorMessage]) {
        toast.update(toastIdRef.current[errorMessage], {
          render: errorMessage,
          autoClose: 3000,
          transition: Slide,
        });
      } else {
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

  const showInvalidWorkflowToast = () => {
    console.error("Workflow ID not found, returning to main.");
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className='app-container' display='flex' flexDirection='column' height='100vh'>
        <ToastContainer />
        
        <Box flexGrow={1} overflow='auto'>
          <Routes>
            <Route path='/' element={<HomePage />} />

            <Route
              path='/create-workflow'
              element={
                <WorkflowLauncher
                  // Pass in the handler that sets up or starts the workflow
                  onWorkflowStart={handleWorkflowStart}
                />
              }
            />

            <Route path='/workflow' element={<Navigate to="/" />} />

            <Route
              path='/workflow/:workflowId'
              element={
                <WorkflowDashboard
                  onWorkflowStateUpdate={handleWorkflowStateUpdate}
                  showInvalidWorkflowToast={showInvalidWorkflowToast}
                  
                  // Pass the entire dictionary of workflowSettings
                  // so the Dashboard can look up the correct toggles for its workflowId
                  workflowSettings={workflowSettings}

                  // Pass a callback so it can update the parent's dictionary
                  onUpdateWorkflowSettings={handleUpdateWorkflowSettings}
                />
              }
            />

            <Route path="/history-logs" element={<LogViewer />} />
            <Route path='' element={<Navigate to="/" />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
