// AgentInteractions.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import SendIcon from '@mui/icons-material/Send';
import PhaseMessage from './components/PhaseMessage/PhaseMessage'; 
import InputContainer from './components/InputContainer/InputContainer';
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
  const [userMessage, setUserMessage] = useState('');
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

  const handleSendMessage = () => {
    if (userMessage.trim()) {
      onSendMessage({
        type: 'user_message',
        content: userMessage
      });
      setUserMessage('');
    }
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

      <Box className="input-and-buttons-container" display="flex">
        {/* <Box className="input-wrapper" flexGrow={1} mr={2}>
          <InputContainer 
            onSendMessage={onSendMessage} 
            setUserMessage={setUserMessage}
            userMessage={userMessage}
          />
        </Box> */}
        <Box className="buttons-wrapper" display="flex" flexDirection="column" justifyContent="flex-end">
          {interactiveMode && (
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={onTriggerNextIteration}
                startIcon={<ArrowForwardIcon />}
                disabled={isNextDisabled}
                size="small"
                sx={{ mb: 1 }}
              >
                Next
              </Button>
              {/* <Button
                variant="contained"
                color="primary"
                onClick={handleSendMessage}
                startIcon={<SendIcon />}
                disabled={!userMessage.trim()}
                size="small"
              >
                Send
              </Button> */}
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default AgentInteractions;