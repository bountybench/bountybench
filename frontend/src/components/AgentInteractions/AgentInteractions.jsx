import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
  workflowStatus, // Pass workflowStatus from parent
  isNextDisabled,
  messages = [],
  onUpdateMessageInput,
  onRerunMessage,
  onTriggerNextIteration,
  onStopWorkflow
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isStopped, setIsStopped] = useState(false);
  const messagesEndRef = useRef(null);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && (event.altKey || !isEditing)) {
      event.preventDefault(); // Prevent the default action
      onTriggerNextIteration();
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isEditing, onTriggerNextIteration]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    console.log('Messages updated:', messages);
  }, [messages]);

  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

  const handleStopClick = async () => {
    setIsStopped(true); // Hide buttons immediately
    await onStopWorkflow();
  };

    // Ensure buttons remain hidden when workflow status updates from parent
    useEffect(() => {
      if (workflowStatus === "stopped") {
        setIsStopped(true);
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
          />
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex" justifyContent="center" gap={1}>
        {interactiveMode && !isStopped && (
          <>
            <Button
              variant="contained"
              color="primary"
              onClick={onTriggerNextIteration}
              startIcon={<KeyboardDoubleArrowRightIcon />}
              disabled={isNextDisabled || isEditing}
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
        )}
      </Box>
    </Box>
  );
};

export default AgentInteractions;
