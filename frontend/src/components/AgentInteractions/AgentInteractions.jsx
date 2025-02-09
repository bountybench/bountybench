import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
  workflowStatus, // Pass workflowStatus from parent
  isNextDisabled,
  phaseMessages = [],
  onUpdateMessageInput,
  onRerunMessage,
  onTriggerNextIteration,
  onStopWorkflow,
  onToggleVersion
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isStopped, setIsStopped] = useState(false);
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
  }, [phaseMessages]);

  useEffect(() => {
    console.log('Phase Messages updated:', phaseMessages);
  }, [phaseMessages]);

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

  if (phaseMessages.length === 0) {
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="interactions-container">
      <Box className="messages-container">
        {phaseMessages.map((phaseMessage, index) => (
          <PhaseMessage
            key={phaseMessage.current_id}
            message={phaseMessage}
            onUpdateMessageInput={onUpdateMessageInput}
            onRerunMessage={onRerunMessage}
            onEditingChange={setIsEditing}            
            isEditing={isEditing}            
            selectedCellId={selectedCellId}
            onCellSelect={setSelectedCellId}
            onToggleVersion={onToggleVersion}
          />
        ))}
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
