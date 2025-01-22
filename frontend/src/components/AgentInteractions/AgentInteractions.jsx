import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import PhaseMessage from './components/PhaseMessage'; 
import InputContainer from './components/InputContainer'; 
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
  currentPhase,
  currentIteration,
  isNextDisabled,
  messages = [],
  onSendMessage,
  onUpdateActionInput,
  onRerunAction,
  onTriggerNextIteration,
}) => {
  const [displayedMessageIndex, setDisplayedMessageIndex] = useState(messages.length - 1);
  const messagesEndRef = useRef(null);

  const filteredMessages = messages.filter(msg => 
    !(msg.message_type === 'AgentMessage' && msg.version_next)
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayedMessageIndex, filteredMessages]);

  useEffect(() => {
    setDisplayedMessageIndex(filteredMessages.length - 1);
  }, [filteredMessages]);

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
        {filteredMessages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No messages yet
          </Typography>
        ) : (
          filteredMessages.slice(0, displayedMessageIndex + 1).map((message, index) => (
            <PhaseMessage
              key={message.id || index}
              message={message}
              onUpdateActionInput={onUpdateActionInput}
              onRerunAction={onRerunAction}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-container" display="flex" alignItems="center">
        {interactiveMode && (
          <InputContainer onSendMessage={onSendMessage} />
        )}
        {interactiveMode && (
          <Button
            variant="contained"
            color="primary"
            onClick={onTriggerNextIteration}
            startIcon={<ArrowForwardIcon />}
            disabled={isNextDisabled}
            size="small"
            sx={{ ml: 2 }}
          >
            Next Iteration
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default AgentInteractions;