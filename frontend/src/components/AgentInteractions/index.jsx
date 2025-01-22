import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, TextField, Button, CircularProgress } from '@mui/material';
import MessageBubble from './components/MessageBubble';
import './AgentInteractions.css';

export const AgentInteractions = ({ 
  workflow, 
  interactiveMode, 
  currentPhase,
  currentIteration,
  messages = [],
  onSendMessage,
  onUpdateActionInput,
  onRerunAction,
}) => {
  console.log('AgentInteractions render, messages:', messages);

  const filteredMessages = messages.filter(msg => {
    if (msg.message_type === 'AgentMessage' && msg.version_next) {
      // This means msg has been superseded by a new version.
      return false;
    }
    return true;
  });

  const [displayedMessageIndex, setDisplayedMessageIndex] = useState(messages.length - 1);
  const messagesEndRef = useRef(null);  
  
  const [userMessage, setUserMessage] = useState('');
  const [textAreaHeight, setTextAreaHeight] = useState('auto');
  const textAreaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [displayedMessageIndex, filteredMessages]);

  useEffect(() => {
    // When a new message is received, update the displayed message index
    setDisplayedMessageIndex(filteredMessages.length - 1);
  }, [filteredMessages]);

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.output?.content) {
        setUserMessage(lastMessage.output.content);
        adjustTextAreaHeight();
      }
    }
  }, [messages]);

  if (!messages) {
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  const handleSendMessage = () => {
    if (userMessage.trim()) {
      onSendMessage({
        type: 'user_message',
        content: userMessage
      });
      setUserMessage('');
    }
  };

  const adjustTextAreaHeight = () => {
    if (textAreaRef.current) {
      console.log("Trying to adjust height")
      textAreaRef.current.style.height = 'auto';
      const newHeight = Math.min(textAreaRef.current.scrollHeight, window.innerHeight * 0.4);
      textAreaRef.current.style.height = `${newHeight}px`;
      setTextAreaHeight(`${newHeight}px`);
    }
  };

  const handleMessageChange = (e) => {
    setUserMessage(e.target.value);
    adjustTextAreaHeight();
  };

  return (
    <Box className="interactions-container">
      <Box className="interactions-header">
        <Typography variant="h6">Agent Interactions</Typography>
        {currentPhase && (
          <Typography variant="subtitle2">
            Phase: {currentPhase.phase_name} - Iteration: {currentIteration?.iteration_number}
          </Typography>
        )}
      </Box>

      <Box className="messages-container">
        {filteredMessages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No messages yet
          </Typography>
        ) : (
          filteredMessages.slice(0, displayedMessageIndex + 1).map((message, index) => (
            <MessageBubble
              key={message.id || index}
              message={message}
              onUpdateActionInput={onUpdateActionInput}
              onRerunAction={onRerunAction}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </Box>

      {interactiveMode && (
        <Box className="input-container">
          <TextField
            fullWidth
            multiline
            inputRef={textAreaRef}
            rows={2}
            variant="outlined"
            placeholder="Type your message..."
            value={userMessage}
            onChange={handleMessageChange}
            sx={{ 
              '& .MuiInputBase-input': {
                color: 'black',
                height: textAreaHeight,
                minHeight: '25px',
                overflow: 'auto',
              },
              border: '1px solid #ccc',
              borderRadius: '6px',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <Button
            variant="contained"
            color="primary"
            onClick={handleSendMessage}
            disabled={!userMessage.trim()}
          >
            Send
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default AgentInteractions;