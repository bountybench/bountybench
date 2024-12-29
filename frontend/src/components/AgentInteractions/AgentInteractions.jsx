import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';

const MessageBubble = ({ message, isAgent, onClick }) => (
  <Box className={`message-container ${isAgent ? 'agent' : 'user'}`} onClick={onClick}>
    <Card className={`message-bubble ${isAgent ? 'agent-bubble' : 'user-bubble'}`}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {isAgent ? message.agent : 'User'}
        </Typography>
        <ReactMarkdown>{message.content}</ReactMarkdown>
        {message.actions && (
          <Box className="action-details">
            <Typography variant="caption" color="text.secondary">
              Actions: {message.actions.length}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  </Box>
);

export const AgentInteractions = ({ 
  workflow, 
  interactiveMode, 
  currentPhase,
  currentIteration,
  onSendMessage 
}) => {
  const [userInput, setUserInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (currentIteration?.messages) {
      setMessages(currentIteration.messages);
    }
  }, [currentIteration]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (userInput.trim()) {
      onSendMessage({
        type: 'user_input',
        content: userInput
      });
      setUserInput('');
    }
  };

  const handleMessageClick = (message) => {
    setSelectedMessage(selectedMessage?.id === message.id ? null : message);
  };

  return (
    <Box className="interactions-container">
      <Box className="interactions-header">
        <Typography variant="h6">Agent Interactions</Typography>
        {currentPhase && (
          <Typography variant="subtitle2">
            Phase: {currentPhase.phase_name} - Iteration: {currentIteration?.iteration_idx + 1}
          </Typography>
        )}
        <Box>
          <IconButton size="small">
            <PlayArrowIcon />
          </IconButton>
          <IconButton size="small">
            <PauseIcon />
          </IconButton>
        </Box>
      </Box>

      <Box className="messages-container">
        {messages.map((message, index) => (
          <MessageBubble
            key={index}
            message={message}
            isAgent={!message.isUser}
            onClick={() => handleMessageClick(message)}
          />
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {selectedMessage && (
        <Box className="message-details">
          <Typography variant="h6">Action Details</Typography>
          {selectedMessage.actions?.map((action, index) => (
            <Card key={index} className="action-card">
              <CardContent>
                <Typography variant="subtitle2">{action.type}</Typography>
                <ReactMarkdown>{action.description}</ReactMarkdown>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {interactiveMode && (
        <Box className="input-container">
          <TextField
            fullWidth
            multiline
            rows={2}
            variant="outlined"
            placeholder="Type your message..."
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
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
            disabled={!userInput.trim()}
          >
            Send
          </Button>
        </Box>
      )}
    </Box>
  );
};
