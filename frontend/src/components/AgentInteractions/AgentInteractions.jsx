import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, CircularProgress, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';

const ActionCard = ({ action }) => {
  // 1) Default to expanded so partial updates are visible
  const [expanded, setExpanded] = useState(true);
  console.log('Rendering action:', action);

  if (!action) return null;

  const formatData = (data) => {
    if (!data) return '';
    if (typeof data === 'string') return data;
    
    // Handle objects with stdout/stderr
    if (data.stdout || data.stderr) {
      return `${data.stdout || ''}\n${data.stderr || ''}`.trim();
    }
    
    // Try parsing as JSON
    try {
      if (typeof data === 'string') {
        const parsed = JSON.parse(data);
        return JSON.stringify(parsed, null, 2);
      }
      return JSON.stringify(data, null, 2);
    } catch (e) {
      return String(data);
    }
  };

  const renderContent = (content, label) => {
    if (!content) return null;
    const formattedContent = formatData(content);
    if (!formattedContent) return null;
    
    // If LLM action with a "response" field, format as markdown
    if (action.action_type === 'llm' && label === 'Output' && content) {
      try {
        const parsed = typeof content === 'string' ? JSON.parse(content) : content;
        if (parsed.response) {
          return (
            <Box mt={1}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                {label}:
              </Typography>
              <Card variant="outlined" sx={{ bgcolor: '#f5f5f5', p: 1 }}>
                <ReactMarkdown>{parsed.response}</ReactMarkdown>
              </Card>
            </Box>
          );
        }
      } catch (e) {
        // fall back to default rendering
      }
    }
    
    // Default rendering
    return (
      <Box mt={1}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          {label}:
        </Typography>
        <Card variant="outlined" sx={{ bgcolor: '#f5f5f5', p: 1 }}>
          <Typography 
            variant="body2" 
            component="pre" 
            sx={{ 
              whiteSpace: 'pre-wrap', 
              overflowX: 'auto',
              m: 0,
              fontFamily: 'monospace',
              fontSize: '0.85rem'
            }}
          >
            {formattedContent}
          </Typography>
        </Card>
      </Box>
    );
  };

  return (
    <Card className="action-card" variant="outlined">
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 'bold' }}>
              {action.action_type.toUpperCase()}
            </Typography>
            {action.timestamp && (
              <Typography variant="caption" color="text.secondary">
                {new Date(action.timestamp).toLocaleTimeString()}
              </Typography>
            )}
          </Box>
          {/* 2) Keep the expand icon if you want to toggle; set expanded=true by default */}
          <IconButton
            onClick={() => setExpanded(!expanded)}
            sx={{ 
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s'
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
        </Box>
        
        <Collapse in={expanded}>
          {renderContent(action.input_data, 'Input')}
          {renderContent(action.output_data, 'Output')}
          {action.metadata && Object.keys(action.metadata).length > 0 && (
            <Box mt={1}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                Metadata:
              </Typography>
              <Card variant="outlined" sx={{ bgcolor: '#f5f5f5', p: 1 }}>
                <Typography 
                  variant="body2" 
                  component="pre" 
                  sx={{ 
                    whiteSpace: 'pre-wrap', 
                    overflowX: 'auto',
                    m: 0,
                    fontFamily: 'monospace',
                    fontSize: '0.85rem'
                  }}
                >
                  {formatData(action.metadata)}
                </Typography>
              </Card>
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

const MessageBubble = ({ message }) => {
  // 3) Default to expanded
  const [expanded, setExpanded] = useState(true);
  console.log('Rendering message:', message);
  
  if (!message) return null;

  const hasContent = message.input?.content || message.output?.content;
  const hasActions = message.actions && message.actions.length > 0;
  const messageClass = message.isSystem ? 'system' : message.isUser ? 'user' : 'agent';
  
  return (
    <Box className={`message-container ${messageClass}`}>
      <Card 
        className={`message-bubble ${messageClass}-bubble`}
        // If you do NOT want toggling on click, remove onClick or the entire cursor pointer
        onClick={() => setExpanded(!expanded)}
        sx={{ cursor: 'pointer' }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {message.agent_name || 'System'}
            </Typography>
            {(hasContent || hasActions) && (
              <IconButton
                size="small"
                sx={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
              >
                <ExpandMoreIcon />
              </IconButton>
            )}
          </Box>
          
          <Collapse in={expanded || message.isSystem}>
            {message.input?.content && (
              <Box mt={1}>
                <Typography variant="caption" color="text.secondary">Input:</Typography>
                <Box sx={{ mt: 1 }}>
                  <ReactMarkdown>{message.input.content}</ReactMarkdown>
                </Box>
              </Box>
            )}
            {message.output?.content && (
              <Box mt={1}>
                <Typography variant="caption" color="text.secondary">Output:</Typography>
                <Box sx={{ mt: 1 }}>
                  <ReactMarkdown>{message.output.content}</ReactMarkdown>
                </Box>
              </Box>
            )}
            {hasActions && (
              <Box mt={2}>
                <Typography variant="subtitle2" gutterBottom>Actions:</Typography>
                {message.actions.map((action, index) => (
                  // 4) Unique key for each action
                  <Box key={`${message.id}_action_${index}`} mt={1}>
                    <ActionCard action={action} />
                  </Box>
                ))}
              </Box>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export const AgentInteractions = ({ 
  workflow, 
  interactiveMode, 
  currentPhase,
  currentIteration,
  messages = [],
  onSendMessage 
}) => {
  console.log('AgentInteractions props:', { 
    workflow, 
    interactiveMode, 
    currentPhase, 
    currentIteration, 
    messageCount: messages?.length,
    messages: messages
  });
  
  const [userInput, setUserInput] = useState('');
  const messagesEndRef = useRef(null);

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

  if (!messages) {
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

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
        {messages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No messages yet
          </Typography>
        ) : (
          messages.map((message, index) => (
            // 5) Unique key per message
            <MessageBubble
              key={message.id || index}
              message={message}
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
