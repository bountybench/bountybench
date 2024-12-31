import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, CircularProgress, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit'; 
import SaveIcon from '@mui/icons-material/Save';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';

const ActionCard = ({ action, onUpdateActionInput }) => {
  // 1) Default to expanded so partial updates are visible
  const [expanded, setExpanded] = useState(true);
  console.log('Rendering action:', action);
  const [editing, setEditing] = useState(false);            // ADDED
  const [editedInput, setEditedInput] = useState('');       // ADDED

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

  // We grab the original input to show if editing.
  const originalInputContent = formatData(action.input_data);

  const renderContent = (content, label) => {
    if (!content) return null;
    const formattedContent = formatData(content);
    if (!formattedContent) return null;

    if (action.action_type === 'llm' && label === 'Input') {
      return (
        <Box mt={1}>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mb: 0.5 }}
            >
              {label}:
            </Typography>
          </Box>
          {editing ? (
            <TextField
              multiline
              fullWidth
              minRows={3}
              maxRows={10}
              value={editedInput}
              onChange={(e) => setEditedInput(e.target.value)}
              sx={{
                mt: 1,
                '& .MuiInputBase-input': {
                  color: 'black',
                },
              }}
            />
          ) : (
            <Card variant="outlined" sx={{ bgcolor: '#f5f5f5', p: 1, mt: 1 }}>
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  whiteSpace: 'pre-wrap',
                  overflowX: 'auto',
                  m: 0,
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                }}
              >
                {formattedContent}
              </Typography>
            </Card>
          )}
          {editing && (
            <Box display="flex" justifyContent="flex-end" mt={1}>
              <Button
                size="small"
                variant="contained"
                color="primary"
                onClick={handleSaveClick}
              >
                Save
              </Button>
            </Box>
          )}
        </Box>
      );
    }
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


  const handleEditClick = () => {
    setEditing(true);
    setEditedInput(formatData(action.input_data)); // Populate with original input
  };

  const handleSaveClick = async () => {
    if (!action.timestamp) {
      console.error('Action ID is undefined');
      return;
    }
    await onUpdateActionInput(action.timestamp, editedInput);
    setEditing(false);
  };

  const handleExpandClick = (e) => {
    e.stopPropagation(); // Prevent event from bubbling up
    setExpanded(!expanded);
  };

  return (
    <Card className="action-card" variant="outlined">
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 'bold' }}>
              {action.action_type ? action.action_type.toUpperCase() : 'ACTION'}
            </Typography>
            {action.timestamp && (
              <Typography variant="caption" color="text.secondary">
                {new Date(action.timestamp).toLocaleTimeString()}
              </Typography>
            )}
          </Box>
          <IconButton
            onClick={handleExpandClick}
            aria-expanded={expanded}
            aria-label="show more"
            sx={{ color: 'black' }} 
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          {editing ? (
            <Box mt={1}>
              <Typography variant="caption" color="text.secondary">
                Editing Input:
              </Typography>
              <TextField
                multiline
                minRows={3}
                maxRows={10}
                value={editedInput}
                onChange={(e) => setEditedInput(e.target.value)}
                sx={{
                  '& .MuiInputBase-input': {
                    color: 'black',
                  },
                }}
                fullWidth
              />
              <Box mt={1} display="flex" justifyContent="flex-end">
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSaveClick}
                  size="small"
                >
                  <SaveIcon/>
                </Button>
              </Box>
            </Box>
          ) : (
            <>
              {renderContent(action.input_data, 'Input')}
              <Box mt={1} display="flex" justifyContent="flex-end">
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={handleEditClick}
                  size="small"
                >
                  <EditIcon />
                </Button>
              </Box>
            </>
          )}

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

export default ActionCard;


const MessageBubble = ({ message, onUpdateActionInput }) => {
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
        // onClick={() => setExpanded(!expanded)}
        sx={{ cursor: 'pointer' }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {message.agent_name || 'System'}
            </Typography>
            {/* {(hasContent || hasActions) && (
              <IconButton
                size="small"
                sx={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
              >
                <ExpandMoreIcon />
              </IconButton>
            )} */}
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
                    <ActionCard 
                      action={action}
                      onUpdateActionInput={onUpdateActionInput}
                    />
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
  onSendMessage,
  onUpdateActionInput,
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
              onUpdateActionInput={onUpdateActionInput} 
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
