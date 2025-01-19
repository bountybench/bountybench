import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, CircularProgress, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit'; 
import SaveIcon from '@mui/icons-material/Save';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';

const ActionCard = ({ action, onUpdateActionInput }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);            
  const [editedMessage, setEditedMessage] = useState(''); 

  if (!action) return null;

  // Format the action message
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

  // Original message content
  const originalMessageContent = formatData(action.message);

  const renderContent = (content, label) => {
    if (!content) return null;
    const formattedContent = formatData(content);
    if (!formattedContent) return null;

    // Customize rendering based on resource_id or other logic if needed
    return (
      <Box mt={1}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          {label}:
        </Typography>
        {editing ? (
          <TextField
            multiline
            fullWidth
            minRows={3}
            maxRows={10}
            value={editedMessage}
            onChange={(e) => setEditedMessage(e.target.value)}
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
              <SaveIcon/>
            </Button>
          </Box>
        )}
      </Box>
    );
  };

  const handleEditClick = () => {
    setEditing(true);
    setEditedMessage(originalMessageContent); // Populate with original message
  };

  const handleSaveClick = async () => {
    if (!action.timestamp) {
      console.error('Action timestamp is undefined');
      return;
    }
    await onUpdateActionInput(action.timestamp, editedMessage);
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
              {action.resource_id ? action.resource_id.toUpperCase() : 'ACTION'}
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
                Editing Message:
              </Typography>
              <TextField
                multiline
                minRows={3}
                maxRows={10}
                value={editedMessage}
                onChange={(e) => setEditedMessage(e.target.value)}
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
              {renderContent(action.message, 'Message')}
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

          {action.additional_metadata && Object.keys(action.additional_metadata).length > 0 && (
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
                  {formatData(action.additional_metadata)}
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
  const [expanded, setExpanded] = useState(true);

  if (!message) return null;

  const handleToggleExpanded = () => setExpanded((prev) => !prev);

  switch (message.message_type) {
    case 'AgentMessage':
      return (
        <Box className={`message-container agent`}>
          <Card className="message-bubble agent-bubble">
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" onClick={handleToggleExpanded} style={{ cursor: 'pointer' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Agent: {message.agent_id}
                </Typography>
                <IconButton size="small">
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={expanded}>
                <Box mt={1}>
                  <ReactMarkdown>{message.message || ''}</ReactMarkdown>
                </Box>

                {message.action_messages && message.action_messages.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2">Actions:</Typography>
                    {message.action_messages.map((action, index) => (
                      <Box key={`action_${index}`} mt={1}>
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

    case 'ActionMessage':
      // If ActionMessage can appear independently
      return (
        <Box className={`message-container action`}>
          <Card className="message-bubble action-bubble">
            <CardContent onClick={handleToggleExpanded} style={{ cursor: 'pointer' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Action on Resource: {message.resource_id}
                </Typography>
                <IconButton size="small">
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={expanded}>
                <Box mt={1}>
                  <ReactMarkdown>{message.message || ''}</ReactMarkdown>
                </Box>
                {message.additional_metadata && (
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
                        {JSON.stringify(message.additional_metadata, null, 2)}
                      </Typography>
                    </Card>
                  </Box>
                )}
              </Collapse>
            </CardContent>
          </Card>
        </Box>
      );

    case 'PhaseMessage':
      return (
        <Box className={`message-container system`}>
          <Card className="message-bubble system-bubble">
            <CardContent onClick={handleToggleExpanded} style={{ cursor: 'pointer' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Phase
                </Typography>
                <IconButton size="small">
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={expanded}>
                <Typography variant="body2" mt={1}>
                  Summary: {message.phase_summary || '(no summary)'}
                </Typography>
                {message.additional_metadata && (
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
                        {JSON.stringify(message.additional_metadata, null, 2)}
                      </Typography>
                    </Card>
                  </Box>
                )}
              </Collapse>
            </CardContent>
          </Card>
        </Box>
      );

    case 'WorkflowMessage':
      return (
        <Box className={`message-container system`}>
          <Card className="message-bubble system-bubble">
            <CardContent onClick={handleToggleExpanded} style={{ cursor: 'pointer' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Workflow
                </Typography>
                <IconButton size="small">
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={expanded}>
                <Typography variant="body2" mt={1}>
                  Name: {message.workflow_metadata?.workflow_name || '(unknown)'}
                </Typography>
                <Typography variant="body2">
                  Summary: {message.workflow_metadata?.workflow_summary || '(none)'}
                </Typography>
                {/* Optionally, render phase_messages or other metadata */}
                {message.workflow_metadata?.phase_messages && message.workflow_metadata.phase_messages.length > 0 && (
                  <Box mt={1}>
                    <Typography variant="subtitle2">Phases:</Typography>
                    {message.workflow_metadata.phase_messages.map((phase, index) => (
                      <Box key={`phase_${index}`} mt={1}>
                        <Typography variant="body2">
                          {phase.phase_summary || 'No summary'}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </Collapse>
            </CardContent>
          </Card>
        </Box>
      );

    default:
      // Fallback for unknown message types
      return (
        <Box className="message-container system">
          <Card className="message-bubble system-bubble">
            <CardContent>
              <Typography variant="subtitle2" color="error">
                Unknown message_type: {message.message_type}
              </Typography>
              <pre>{JSON.stringify(message, null, 2)}</pre>
            </CardContent>
          </Card>
        </Box>
      );
  }
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
  
  const [userMessage, setUserMessage] = useState('');
  const messagesEndRef = useRef(null);
  const [textAreaHeight, setTextAreaHeight] = useState('auto');
  const textAreaRef = useRef(null);


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchLastMessage = async () => {
    try {
      const response = await fetch(`http://localhost:8000/workflow/last-message/${workflow.id}`); 
      if (response.ok) {
        const lastMessage = await response.json();
        setUserMessage(lastMessage.content);
        adjustTextAreaHeight();
      }
    } catch (error) {
      console.error('Failed to fetch last message:', error);
    }
  };

  const fetchFirstMessage = async () => {
    try {
      const response = await fetch(`http://localhost:8000/workflow/first-message/${workflow.id}`); 
      if (response.ok) {
        const firstMessage = await response.json();
        setUserMessage(firstMessage.content);
        adjustTextAreaHeight();
      }
    } catch (error) {
      console.error('Failed to fetch last message:', error);
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      fetchLastMessage();
    } else {
      fetchFirstMessage();
    }
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

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.output?.content) {
        setUserMessage(lastMessage.output.content);
        adjustTextAreaHeight();
      }
    }
  }, [messages]);

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
