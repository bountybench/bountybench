import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
  isNextDisabled,
  messages = [],
  onUpdateMessageInput,
  onRerunMessage,
  onTriggerNextIteration,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const messagesEndRef = useRef(null);
  const cellRefs = useRef({}); 
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

  // Find the latest PhaseMessage
  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

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
            cellRefs={cellRefs}
          />
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex">
        <Box className="buttons-wrapper" display="flex" flexDirection="column" justifyContent="flex-end">
          {interactiveMode && (
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={onTriggerNextIteration}
                startIcon={<KeyboardDoubleArrowRightIcon />}
                disabled={isNextDisabled || isEditing}
                size="small"
                sx={{ mb: 1 }}
              >
                Continue
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default AgentInteractions;