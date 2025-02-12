import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';
import ReplayIcon from '@mui/icons-material/Replay';

const AgentInteractions = ({ 
  interactiveMode, 
  workflowStatus, // Pass workflowStatus from parent
  isNextDisabled,
  messages = [],
  onUpdateMessageInput,
  onRerunMessage,
  onTriggerNextIteration,
  onStopWorkflow,
  onRestart
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [stopped, setStopped] = useState(false);
  const messagesEndRef = useRef(null);
  const [selectedCellId, setSelectedCellId] = useState(null);

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && event.altKey) {
      event.preventDefault(); // Prevent the default action
      onTriggerNextIteration();
    }
  }, [onTriggerNextIteration]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isEditing, handleKeyDown, onTriggerNextIteration]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    console.log('Messages updated:', messages);
  }, [messages]);

  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

  const handleStopClick = async () => {
    setIsStopping(true); // Hide buttons immediately
    await onStopWorkflow();
    setStopped(true);
  };

  const handleRestart = async (w) => {
    await onRestart();
  };

    // Ensure buttons remain hidden when workflow status updates from parent
    useEffect(() => {
      if (workflowStatus === "stopped") {
        setIsStopping(true);
        setStopped(true);
      }
      else {
        setIsStopping(false);
        setStopped(false);
      }
    }, [workflowStatus]);
  

  if (!messages) {
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="interactions-container">
      <Box className="messages-container">
        {!latestPhaseMessage ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No Phase messages yet
          </Typography>
        ) : (
          <PhaseMessage
            message={latestPhaseMessage}
            onUpdateMessageInput={onUpdateMessageInput}
            onRerunMessage={onRerunMessage}
            onEditingChange={setIsEditing}            
            isEditing={isEditing}            
            selectedCellId={selectedCellId}
            onCellSelect={setSelectedCellId}
          />
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex" justifyContent="center" gap={1}>
      {interactiveMode && (
        <>
        {!isStopping && !stopped ? (
          <>
            <Button
              variant="contained"
              color="primary"
              onClick={onTriggerNextIteration}
              startIcon={<KeyboardDoubleArrowRightIcon />}
              disabled={isNextDisabled}
              size="small"
            >
              Continue
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={handleStopClick}
              startIcon={<StopIcon />}
              size="small"
            >
              Stop
            </Button>
          </>
        ) : null}
        {isStopping && stopped && (
          <Button
            variant="contained"
            color="primary"
            onClick={handleRestart}
            startIcon={<ReplayIcon />}
            size="small"
          >
            Restart
          </Button>
          )}
        </>
      )}
      </Box>
    </Box>
  );
};

export default AgentInteractions;
