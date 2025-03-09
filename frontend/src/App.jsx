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
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [interactiveMode, setInteractiveMode] = useState(true);
  const [useMockModel, setUseMockModel] = useState(false); 
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const toastIdRef = useRef({});

  const handleWorkflowStart = (workflowId, model, isInteractive, useMockModel) => {
    console.log("=============handleWorkflowStart:=============", { workflowId, model, isInteractive, useMockModel });
    setSelectedWorkflow({ id: workflowId, model: model });
    setInteractiveMode(isInteractive);
    setUseMockModel(useMockModel)
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
        <Box flexGrow={1} overflow='auto'>
          <Routes>
            <Route path='/' element={<HomePage/>} />
            <Route path='/create-workflow' element={
              <WorkflowLauncher 
                onWorkflowStart={handleWorkflowStart} 
                interactiveMode={interactiveMode} 
                setInteractiveMode={setInteractiveMode} 
                useMockModel={useMockModel} 
                setUseMockModel={setUseMockModel} 
              />
            } />
            <Route path='/workflow' element={<Navigate to="/" />} />
            <Route path='/workflow/:workflowId' 
              element={
                <WorkflowDashboard 
                  interactiveMode={interactiveMode} 
                  onWorkflowStateUpdate={handleWorkflowStateUpdate} 
                  showInvalidWorkflowToast={showInvalidWorkflowToast}
                  useMockModel={useMockModel}
                  setUseMockModel={setUseMockModel}
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