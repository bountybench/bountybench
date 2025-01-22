import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, CircularProgress, Collapse, Divider } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit'; 
import SaveIcon from '@mui/icons-material/Save';
import ReactMarkdown from 'react-markdown';
import './AgentInteractions.css';
import ReplayIcon from '@mui/icons-material/Replay';

const ActionCard = ({ action, onUpdateActionInput, onRerunAction }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);            
  const [editedMessage, setEditedMessage] = useState(''); 
  const [metadataExpanded, setMetadataExpanded] = useState(false);

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

  const handleToggleMetadata = (event) => {
    event.stopPropagation();
    setMetadataExpanded(!metadataExpanded);
  };

  const handleRerunClick = async () => {
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onRerunAction(action.current_id);
    } catch (error) {
      console.error('Error rerunning action:', error);
    }
  };

  // Original message content
  const originalMessageContent = formatData(action.message);

  const renderContent = (content, label) => {
    if (!content) return null;
    const formattedContent = formatData(content);
    if (!formattedContent) return null;

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
    if (!action.current_id) { // Changed from message to action
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
                <Button
                  variant="outlined"
                  color="secondary"
                  onClick={handleRerunClick}
                  size="small"
                >
                  <ReplayIcon />
                </Button>
              </Box>
            </>
          )}


          {/* Metadata section */}
          {action.additional_metadata && (
            <Box mt={2}>
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
                onClick={handleToggleMetadata}
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
                    Click here to show metadata:
                    <IconButton size="small" sx={{ ml: 1, p: 0.5 }}>
                    {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </Typography>
              </Box>
              
              <Collapse in={metadataExpanded}>
                <Box mt={1}>
                  <Card 
                    variant="outlined" 
                    sx={{ bgcolor: '#f5f5f5', p: 1 }}
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
                      {JSON.stringify(action.additional_metadata, null, 2)}
                    </Typography>
                  </Card>
                </Box>
              </Collapse>
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default ActionCard;


const MessageBubble = ({ message, onUpdateActionInput, onRerunAction }) => {
  console.log(`Rendering MessageBubble for message ID: ${message.current_id}`);

  const [contentExpanded, setContentExpanded] = useState(true);
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(
    message.agent_id === 'system' || message.agent_id === 'human'
  );  const [editing, setEditing] = useState(false); // Added missing state
  const [editedMessage, setEditedMessage] = useState(''); // Added missing state



  if (!message) return null;

  const handleToggleContent = (event) => {
    event.stopPropagation();
    setContentExpanded(!contentExpanded);
  };

  const handleToggleAgentMessage = (event) => {
    event.stopPropagation();
    setAgentMessageExpanded(!agentMessageExpanded);
  };

  const handleEditClick = () => {
    setEditing(true);
    setEditedMessage(message.message || '');
  };

  const handleSaveClick = async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(message.current_id, editedMessage);
      setEditing(false);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  };


  const renderActionMessage = (actionMessage) => (
    <ActionCard
      key={actionMessage.current_id}
      action={actionMessage}
      onUpdateActionInput={onUpdateActionInput}
      onRerunAction={onRerunAction}
    />
  );

  switch (message.message_type) {
    case 'AgentMessage':
    return (
      <Box
        className={`message-container ${message.agent_id}`}
        sx={{
          width: '100%', // Ensure it takes the full width of the container
          maxWidth: '800px', // Set a reasonable maximum width
          margin: '0 auto', // Center the component horizontally
        }}
      >
        <Card 
          className="message-bubble agent-bubble"
          sx={{
            backgroundColor: '#f0f4f8 !important',
            '& .MuiCardContent-root': {
              backgroundColor: '#f0f4f8 !important',
            },
            '& .action-bubble': {
              boxShadow: 1,
            },
            p: 2,
            width: '100%', // Ensure the card spans the full container width
          }}
        >
          <CardContent>
            <Typography variant="subtitle1" sx={{ mb: 2 }}>
              Agent: {message.agent_id}
            </Typography>

            {message.current_children && message.current_children.length > 0 && (
              <Box
                sx={{
                  mt: 2,
                  '& .message-container.action': {
                    px: 0,
                  },
                }}
              >
                {message.current_children.map((actionMessage, index) => (
                  <Box key={index}>
                    {renderActionMessage(actionMessage)}
                  </Box>
                ))}
              </Box>
            )}

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
                    fontWeight: 'medium',
                  }}
                >
                  Click here to show {message.agent_id} output:
                  <IconButton size="small" sx={{ ml: 1, p: 0.5 }}>
                    {agentMessageExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Typography>
              </Box>

              <Collapse in={agentMessageExpanded}>
                <Box mt={1}>
                  {editing ? (
                    <Box>
                      <TextField
                        multiline
                        fullWidth
                        minRows={3}
                        maxRows={10}
                        value={editedMessage}
                        onChange={(e) => setEditedMessage(e.target.value)}
                        sx={{
                          '& .MuiInputBase-input': {
                            color: 'black',
                            minHeight: '75px', // Minimum height for text box
                            maxHeight: '400px', // Limit maximum height
                            overflow: 'auto',
                          },
                        }}
                      />
                      <Box mt={1} display="flex" justifyContent="flex-end">
                        <Button
                          variant="contained"
                          color="primary"
                          onClick={handleSaveClick}
                          size="small"
                        >
                          <SaveIcon />
                        </Button>
                      </Box>
                    </Box>
                  ) : (
                    <>
                      <Card
                        variant="outlined"
                        sx={{
                          bgcolor: '#e5e9f0 !important',
                          '& .MuiCardContent-root': {
                            backgroundColor: '#e5e9f0 !important',
                          },
                          p: 1,
                          width: '100%', // Ensure the card takes full width
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
                            fontSize: '0.85rem',
                          }}
                        >
                          {message.message || ''}
                        </Typography>
                      </Card>
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
    <Box
      className="message-container system"
      sx={{
        mb: 2,
        width: '100%', // Ensure full width of the parent container
        maxWidth: '95%', // Make it nearly full-screen but leave slight margins
        margin: '0 auto', // Center the content horizontally
      }}
    >
      {/* Optionally show a minimal summary */}
      {message.phase_summary && (
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
          Phase Summary: {message.phase_summary}
        </Typography>
      )}

      {/* Render the canonical list of AgentMessages (PhaseMessage.current_agent_list) */}
      {message.current_children && message.current_children.length > 0 && (
        <Box
          sx={{
            width: '100%', // Ensure child content matches the parent width
          }}
        >
          {message.current_children.map((agentMsg, index) => (
            <MessageBubble
              key={agentMsg.id || index}
              message={agentMsg}
              onUpdateActionInput={onUpdateActionInput}
              onRerunAction={onRerunAction}
            />
          ))}
        </Box>
      )}

      {/* If you have any phase-level metadata, display it without a collapse: */}
      {message.additional_metadata && (
        <Box
          mt={1}
          sx={{
            bgcolor: '#f5f5f5',
            p: 2,
            width: '100%',
            maxWidth: '95%', // Match the wider width
            overflowX: 'auto',
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
              fontSize: '0.85rem',
            }}
          >
            {JSON.stringify(message.additional_metadata, null, 2)}
          </Typography>
        </Box>
      )}
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
  onSendMessage,
  onUpdateActionInput,
  onRerunAction,
}) => {
  console.log('AgentInteractions render, messages:', messages);

  const messagesEndRef = useRef(null);
  const [userMessage, setUserMessage] = useState('');
  const [textAreaHeight, setTextAreaHeight] = useState('auto');
  const textAreaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    console.log('Messages updated:', messages);
  }, [messages]);

  // Find the latest PhaseMessage
  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  console.log('Latest PhaseMessage:', latestPhaseMessage);

  // Function to get the latest version of a message using version_next
  const getLatestVersion = (msg, allAgentMessages) => {
    let latest = msg;
    let depth = 0;
    const maxDepth = 10; // Prevent infinite loops
    console.log(`Traversing versions for message ID: ${msg.current_id}`);
    while (latest.version_next && depth < maxDepth) {
      const versionNextStr = String(latest.version_next); // Ensure it's a string
      console.log(`Looking for version_next ID: ${versionNextStr}`);
      const nextVersion = allAgentMessages.find(child => {
        console.log(`Checking child with current_id: ${child.current_id} (type: ${typeof child.current_id})`);
        return child.current_id === versionNextStr;
      });
      if (!nextVersion) {
        console.warn(`No message found with ID: ${versionNextStr}`);
        break;
      }
      console.log(`Found next version: ${nextVersion.current_id}`);
      latest = nextVersion;
      depth += 1;
    }
    if (depth === maxDepth) {
      console.warn(`Max traversal depth reached for message ID: ${msg.current_id}`);
    }
    console.log(`Latest version found: ${latest.current_id}`);
    return latest;
  };

  // Function to render ActionMessage
  const renderActionMessage = (actionMsg, index) => (
    <ActionCard
      key={`action-${actionMsg.current_id || index}`}
      action={actionMsg}
      onUpdateActionInput={onUpdateActionInput}
      onRerunAction={onRerunAction}
    />
  );

  // Function to render AgentMessage
  const renderAgentMessage = (agentMsg, index, allAgentMessages) => {
    const latestVersion = getLatestVersion(agentMsg, allAgentMessages);
    console.log(`Rendering AgentMessage ID: ${latestVersion.current_id}`);
    return (
      <MessageBubble
        key={`agent-${latestVersion.current_id}`}
        message={latestVersion}
        onUpdateActionInput={onUpdateActionInput}
        onRerunAction={onRerunAction}
      />
    );
  };

  // Function to render PhaseMessage
  const renderPhaseMessage = (phaseMessage) => {
    if (!phaseMessage) return null;

    const allAgentMessages = phaseMessage.agent_messages || [];
    console.log('All Agent Messages:', allAgentMessages);

    // Identify root messages (messages without version_prev)
    const rootMessages = allAgentMessages.filter(msg => !msg.version_prev);
    console.log('Root Agent Messages:', rootMessages);

    return (
      <Box className="phase-message">
        <Typography variant="h6">Phase: {phaseMessage.phase_id}</Typography>
        <Typography variant="body2">Summary: {phaseMessage.phase_summary}</Typography>
        {rootMessages.map((agentMsg, index) => (
          renderAgentMessage(agentMsg, index, allAgentMessages)
        ))}
      </Box>
    );
  };

  // Adjust TextArea Height Function
  const adjustTextAreaHeight = () => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
      const newHeight = Math.min(textAreaRef.current.scrollHeight, window.innerHeight * 0.4);
      textAreaRef.current.style.height = `${newHeight}px`;
      setTextAreaHeight(`${newHeight}px`);
    }
  };

  // Handle User Message Change
  const handleMessageChange = (e) => {
    setUserMessage(e.target.value);
    adjustTextAreaHeight();
  };

  // Handle Sending Message
  const handleSendMessage = () => {
    if (userMessage.trim()) {
      onSendMessage({ type: 'user_message', content: userMessage });
      setUserMessage('');
      adjustTextAreaHeight();
    }
  };

  return (
    <Box className="interactions-container">
      <Box className="interactions-header">
        <Typography variant="h6">Agent Interactions</Typography>
        {currentPhase && (
          <Typography variant="subtitle2">
            Phase: {currentPhase.phase_id} - Iteration: {currentIteration?.iteration_number}
          </Typography>
        )}
      </Box>

      <Box className="messages-container">
        {!latestPhaseMessage ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No Phase messages yet
          </Typography>
        ) : (
          renderPhaseMessage(latestPhaseMessage)
        )}
        <div ref={messagesEndRef} />
      </Box>

      {interactiveMode && (
        <Box className="input-container" display="flex" alignItems="center" mt={2}>
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
              mr: 2, // Add margin to the right for spacing
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
            startIcon={<SaveIcon />}
          >
            Send
          </Button>
        </Box>
      )}
    </Box>
  );
};