import React from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Alert } from '@mui/material';
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
  const [socket, setSocket] = React.useState(null);
  const [isConnected, setIsConnected] = React.useState(false);
  const [error, setError] = React.useState(null);
  const messagesEndRef = React.useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    if (workflow?.id && !socket) {
      const ws = new WebSocket(`ws://localhost:8000/ws/workflow/${workflow.id}`);
      
      ws.onopen = () => {
        console.log('WebSocket Connected');
        setIsConnected(true);
        setError(null);
      };
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'agent_response') {
          setMessages(prev => [...prev, {
            content: message.content,
            agent: message.agent,
            isUser: false
          }]);
        } else if (message.type === 'error') {
          setError(message.content);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket Disconnected');
        setIsConnected(false);
        setSocket(null);
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        setError('Connection error. Please try again later.');
        setIsConnected(false);
      };
      
      setSocket(ws);
      
      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [workflow?.id]);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (userInput.trim() && socket && isConnected) {
      const message = {
        type: 'user_input',
        content: userInput
      };
      
      try {
        socket.send(JSON.stringify(message));
        
        setMessages(prev => [...prev, {
          content: userInput,
          isUser: true
        }]);
        
        setUserInput('');
        setError(null);
      } catch (err) {
        setError('Failed to send message. Please try again.');
      }
    }
  };

  return (
    <Box className="interactions-container">
      <Box className="interactions-header">
        <Typography variant="h6">Agent Interactions</Typography>
        <Box>
          <IconButton size="small" disabled={!isConnected}>
            <PlayArrowIcon />
          </IconButton>
          <IconButton size="small" disabled={!isConnected}>
            <PauseIcon />
          </IconButton>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" className="interactions-alert" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

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
            disabled={!isConnected}
          />
        </Box>
      )}
    </Box>
  );
};
