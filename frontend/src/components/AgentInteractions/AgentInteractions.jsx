import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, CircularProgress, Collapse, Divider } from '@mui/material';
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
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(action.current_id, editedMessage);
      setEditing(false);
    } catch (error) {
      console.error('Error updating action message:', error);
    }
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
          <Box>
            {editing ? (
              <Button
                variant="contained"
                color="primary"
                onClick={handleSaveClick}
                size="small"
                sx={{ mr: 1 }}
              >
                <SaveIcon />
              </Button>
            ) : (
              <Button
                variant="outlined"
                color="primary"
                onClick={handleEditClick}
                size="small"
                sx={{ mr: 1 }}
              >
                <EditIcon />
              </Button>
            )}
            <IconButton
              onClick={handleExpandClick}
              aria-expanded={expanded}
              aria-label="show more"
              sx={{ color: 'black' }}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
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
              Click here to show metadata:
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
  const [metadataExpanded, setMetadataExpanded] = useState(false);
  const [contentExpanded, setContentExpanded] = useState(true);
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(false); // New state for agent message


  if (!message) return null;

  const handleToggleMetadata = (event) => {
    event.stopPropagation();
    setMetadataExpanded(!metadataExpanded);
  };

  const handleToggleContent = (event) => {
    event.stopPropagation();
    setContentExpanded(!contentExpanded);
  };

  const handleToggleAgentMessage = (event) => {
    event.stopPropagation();
    setAgentMessageExpanded(!agentMessageExpanded);
  };


  const renderActionMessage = (actionMessage) => (
    <ActionCard
      key={actionMessage.current_id}
      action={actionMessage}
      onUpdateActionInput={onUpdateActionInput}
    />
  );

  switch (message.message_type) {
    case 'AgentMessage':
    return (
      <Box className={`message-container ${message.agent_id}`}>
        <Card 
          className="message-bubble agent-bubble"
          sx={{
            backgroundColor: '#f0f4f8 !important',
            '& .MuiCardContent-root': {
              backgroundColor: '#f0f4f8 !important'
            },
            '& .action-bubble': {
              boxShadow: 1,
            },
            p: 2
          }}
        >
          <CardContent>
            {/* Agent header */}
            <Typography variant="subtitle1" sx={{ mb: 2 }}>Agent: {message.agent_id}</Typography>

            {/* Action messages nested inside */}
            {message.action_messages && message.action_messages.length > 0 && (
              <Box sx={{ 
                mt: 2,
                '& .message-container.action': {
                  px: 0
                }
              }}>
                {message.action_messages.map((actionMessage, index) => (
                  <Box key={index}>
                    {renderActionMessage(actionMessage)}
                  </Box>
                ))}
              </Box>
            )}

            
            {/* Show Output section */}
            <Box mt={1}>
              <Box 
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  py: 0.5,
                  '&:hover': {
                    bgcolor: 'rgba(0, 0, 0, 0.04)',
                  },
                }}
                onClick={handleToggleAgentMessage}
              >
                <Typography 
                  variant="caption" 
                  color="text.secondary" 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    fontWeight: 'medium'
                  }}
                >
                  Click here to show  {message.agent_id} output:
                  <IconButton size="small" sx={{ ml: 1, p: 0.5 }}>
                    {agentMessageExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </Typography>
              </Box>
              
              <Collapse in={agentMessageExpanded}>
                <Box mt={1}>
                  <Card 
                    variant="outlined" 
                    sx={{ 
                      bgcolor: '#e5e9f0 !important',
                      '& .MuiCardContent-root': {
                        backgroundColor: '#e5e9f0 !important'
                      },
                      p: 1 
                    }}
                  >
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
                      {message.message || ''}
                    </Typography>
                  </Card>
                </Box>
              </Collapse>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
      
    case 'ActionMessage':
      return renderActionMessage(message);

    case 'PhaseMessage':
      return (
        <Box className={`message-container system`}>
          <Card className="message-bubble system-bubble">
            <CardContent onClick={handleToggleContent} style={{ cursor: 'pointer' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Phase
                </Typography>
                <IconButton size="small">
                  {contentExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={contentExpanded}>
                <Typography variant="body2" mt={1}>
                  Summary: {message.phase_summary || '(no summary)'}
                </Typography>
                {message.additional_metadata && (
                  <Box mt={1}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    Click here to show metadata:
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
            <CardContent onClick={handleToggleContent} style={{ cursor: 'pointer' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Workflow
                </Typography>
                <IconButton size="small">
                  {contentExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
              <Collapse in={contentExpanded}>
                <Typography variant="body2" mt={1}>
                  Name: {message.workflow_metadata?.workflow_name || '(unknown)'}
                </Typography>
                <Typography variant="body2">
                  Summary: {message.workflow_metadata?.workflow_summary || '(none)'}
                </Typography>
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
  onUpdateActionInput,
}) => {
  console.log('AgentInteractions render, messages:', messages);
  const [displayedMessageIndex, setDisplayedMessageIndex] = useState(messages.length - 1);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [displayedMessageIndex]);

  useEffect(() => {
    // When a new message is received, update the displayed message index
    setDisplayedMessageIndex(messages.length - 1);
  }, [messages]);

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
          messages.slice(0, displayedMessageIndex + 1).map((message, index) => (
            <MessageBubble
              key={message.id || index}
              message={message}
              onUpdateActionInput={onUpdateActionInput} 
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </Box>
    </Box>
  );
};