import React from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';

const MessageBubble = ({ message, isAgent }) => (
  <Box className={`message-container ${isAgent ? 'agent' : 'user'}`}>
    <Card className={`message-bubble ${isAgent ? 'agent-bubble' : 'user-bubble'}`}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {isAgent ? message.agent : 'User'}
        </Typography>
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </CardContent>
    </Card>
  </Box>
);

export const AgentInteractions = ({ workflow, interactiveMode }) => {
  const [userInput, setUserInput] = React.useState('');
  const [messages, setMessages] = React.useState([]);
  const messagesEndRef = React.useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (userInput.trim()) {
      setMessages([...messages, { content: userInput, isUser: true }]);
      setUserInput('');
    }
  };

  return (
    <Box className="interactions-container">
      <Box className="interactions-header">
        <Typography variant="h6">Agent Interactions</Typography>
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
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} isAgent={!msg.isUser} />
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {interactiveMode && (
        <Box className="input-container">
          <TextField
            fullWidth
            variant="outlined"
            size="small"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            className="message-input"
          />
        </Box>
      )}
    </Box>
  );
};
