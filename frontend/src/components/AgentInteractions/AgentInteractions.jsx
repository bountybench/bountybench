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
  const [userMessage, setUserMessage] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    console.log('Messages updated:', messages);
  }, [messages]);

  const handleSendMessage = () => {
    if (userMessage.trim()) {
      onSendMessage({
        type: 'user_message',
        content: userMessage
      });
      setUserMessage('');
    }
  };

  // Find the latest PhaseMessage
  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

  if (!messages) {
    return (
      <Box className="phase-message">
        <Typography variant="h6">Phase: {phaseMessage.phase_id}</Typography>
        <Typography variant="body2">Summary: {phaseMessage.phase_summary}</Typography>
        {rootMessages.map((agentMsg, index) => (
          renderAgentMessage(agentMsg, index, allAgentMessages)
        ))}
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
            onUpdateActionInput={onUpdateActionInput}
            onRerunAction={onRerunAction}
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
                startIcon={<ArrowForwardIcon />}
                disabled={isNextDisabled}
                size="small"
                sx={{ mb: 1 }}
              >
                Next
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default AgentInteractions;