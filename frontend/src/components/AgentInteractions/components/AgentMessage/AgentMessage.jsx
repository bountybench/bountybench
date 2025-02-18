import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import ActionMessage from '../ActionMessage/ActionMessage';
import { formatData } from '../../utils/messageFormatters';
import './AgentMessage.css';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import AddIcon from '@mui/icons-material/Add';

const AgentMessage = ({ message, onUpdateMessageInput, onRunMessage, onEditingChange, isEditing, selectedCellId, onCellSelect, onToggleVersion }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message?.message || '');
  const textFieldRef = useRef(null);
  
  const [originalMessageContent, setOriginalMessageContent] = useState(formatData(message?.message || ''));
  
  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    onEditingChange(false);
    setEditedMessage(originalMessageContent);
  }, [originalMessageContent, onEditingChange]);
  
  const handleEditClick = useCallback(() => {
    if (!message?.current_children || message?.current_children.length === 0) {
      setEditing(true);
      onEditingChange(true);
      setEditedMessage(originalMessageContent);
    }
  }, [originalMessageContent, onEditingChange, message]);

  const handleSaveClick = useCallback(async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      setOriginalMessageContent(editedMessage);
      setEditing(false);
      onEditingChange(false);
      await onUpdateMessageInput(message.current_id, editedMessage);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  }, [message, editedMessage, onEditingChange, onUpdateMessageInput]);

  const handleRunClick = useCallback(async () => {
    if (!message.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onRunMessage(message.current_id);
    } catch (error) {
      console.error('Error running action:', error);
    }
  }, [message, onRunMessage]);

  useEffect(() => {
    setOriginalMessageContent(message?.message);
  }, [message]);

  useEffect(() => {
    if (editing) {
      setEditedMessage(originalMessageContent);
      if (textFieldRef.current) {
        setTimeout(() => {
          textFieldRef.current.focus();   // Focus the text field when editing starts
          textFieldRef.current.setSelectionRange(0, 0); // Set cursor at the start
        }, 0);
      }
    }
  }, [editing, originalMessageContent]);
  
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (selectedCellId === message?.current_id) {
        if (event.key === 'Escape' && editing) {
          handleCancelEdit();
        }
        else if (event.shiftKey && event.key === 'Enter') {
          event.preventDefault(); // Prevent the default action 
          if (editing) {
            handleSaveClick();      // Call the save function
          } else {
            handleRunClick();
          }
        }
        else if (event.key === 'Enter' && !event.altKey && !editing) {
          handleEditClick();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [editing, message, handleCancelEdit, handleEditClick, handleSaveClick, handleRunClick, selectedCellId]);

  if (!message) return null;

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleContainerClick = (e) => {
    e.stopPropagation();
    onCellSelect(message.current_id);
  };


  return (    
    <Box className={`agent-message-container ${selectedCellId === message.current_id ? 'selected' : ''}`}
      onClick={handleContainerClick}
    >
      <Card className="message-bubble agent-bubble">
        <CardContent>
          <Box className="agent-message-header">
            <Box>
              <Typography className="agent-name">Agent: {message.agent_id}</Typography>
              {message.timestamp && (
                <Typography className="message-timestamp">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </Typography>
              )}
            </Box>
            <IconButton 
              size="small" 
              onClick={handleToggleAgentMessage} 
              className="agent-toggle-button"
            >
              {agentMessageExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          <Collapse in={agentMessageExpanded}>
          {!message.current_children || message.current_children.length === 0 ? (
             <Box className="agent-message-content">
              {editing ? (
                <Box className="edit-mode-container">
                  <TextField className="agent-message-text message-edit-field"
                    inputRef={textFieldRef}
                    multiline
                    fullWidth
                    minRows={3}
                    value={editedMessage}
                    onChange={(e) => setEditedMessage(e.target.value)}
                  />
                  <Box className="message-buttons">
                    <Button
                      variant="outlined"
                      color="secondary"
                      onClick={handleCancelEdit}
                      size="small"
                      aria-label="cancel"
                      className="cancel-button"
                    >
                      <CloseIcon/>
                    </Button>
                    <Button
                      variant="outlined"
                      color="primary"
                      onClick={handleSaveClick}
                      size="small"
                      aria-label="save"
                      className="save-button"
                      sx={{ mr: 1 }}
                    >
                      <KeyboardArrowRightIcon/>
                    </Button>     
                  </Box>
                </Box>
              ) : (
                <Box className="display-mode-container">
                  <Card className="agent-message-text-card">
                    <Typography
                      component="pre"
                      className="agent-message-text"
                    >
                      {originalMessageContent}
                    </Typography>
                  </Card>
                  <Box className="message-buttons">
                    <Button
                      variant="outlined"
                      color="primary"
                      onClick={handleEditClick}
                      size="small"
                      aria-label="edit"
                      className="edit-button"
                    >
                      <EditIcon />
                    </Button>
                    <Button
                      variant="outlined"
                      color="secondary"
                      onClick={handleRunClick}
                      size="small"
                      aria-label="run"
                      className="run-button"
                    >
                      <KeyboardArrowRightIcon />
                    </Button>

                      <>
                        <Typography variant="caption" sx={{ mx: 1 }}>
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          {/* Arrow Buttons */}
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <IconButton
                              aria-label="arrow back"
                              disabled={!message?.version_prev}
                              sx={{ color: 'black' }}
                              size="small"
                              onClick={() => onToggleVersion(message.current_id, 'prev')}
                            >
                              <ArrowBackIcon />
                            </IconButton>
                            <IconButton
                              aria-label="arrow forward"
                              disabled={!message?.version_next}
                              sx={{ color: 'black' }}
                              size="small"
                              onClick={() => onToggleVersion(message.current_id, 'next')}
                            >
                              <ArrowForwardIcon />
                            </IconButton>
                          </Box>

                          {/* Version Number */}
                          {(message?.version_next || message?.version_prev) && (
                          <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                          {message.versions.indexOf(message.current_id) + 1}/{message.versions.length}
                          </Typography>
                          )}
                        </Box>
                      </> 
                  </Box>
                </Box>
              )}
            </Box>
          ) : (
            <>
            <Box className="action-messages-container">
                {message.current_children.map((actionMessage, index) => (
                  <ActionMessage
                    key={actionMessage.current_id}
                    index={index}
                    action={actionMessage}
                    onUpdateMessageInput={onUpdateMessageInput}
                    onRunMessage={onRunMessage}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}                    
                    selectedCellId={selectedCellId}
                    onCellSelect={onCellSelect}
                  />
                ))}
                {/* <Box className="add-action-button-container">
                  <Button
                    variant="outlined"
                    aria-label="action add"
                    size="small"
                    className="add-action-button"
                  >
                    <AddIcon />
                  </Button>
                </Box> */}
              </Box>
              
              <>
              <Typography variant="caption" sx={{ mx: 1 }}>
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {/* Arrow Buttons */}
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <IconButton
                    aria-label="arrow back"
                    disabled={!message?.version_prev}
                    sx={{ color: 'black' }}
                    size="small"
                    onClick={() => onToggleVersion(message.current_id, 'prev')}
                  >
                    <ArrowBackIcon />
                  </IconButton>
                  <IconButton
                    aria-label="arrow forward"
                    disabled={!message?.version_next}
                    sx={{ color: 'black' }}
                    size="small"
                    onClick={() => onToggleVersion(message.current_id, 'next')}
                  >
                    <ArrowForwardIcon />
                  </IconButton>
                </Box>

                {/* Version Number */}
                {(message?.version_next || message?.version_prev) && (
                <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                {message.versions.indexOf(message.current_id) + 1}/{message.versions.length}
                </Typography>
                )}
              </Box>
            </> 
            </>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AgentMessage;