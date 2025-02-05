import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    console.log('Messages updated:', messages);
  }, [messages]);

  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

  const handleStopClick = async () => {
    await onStopWorkflow();
    setIsStopped(true);
  };

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
              startIcon={<ArrowForwardIcon />}
              disabled={isNextDisabled || isEditing}
              size="small"
            >
              Next
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
