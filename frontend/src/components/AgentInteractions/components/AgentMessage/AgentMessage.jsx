import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const AgentMessage = ({ message, onUpdateActionInput, onRerunAction, onEditingChange, isEditing, selectedCellId, onCellSelect, cellRefs, onPhaseChildUpdate, phaseDisplayedIndex, phaseVersionLength }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message ? message.message || '' : '');

  const [displayedIndex, setDisplayedIndex] = useState(1);
  
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (selectedCellId === message.current_id) {
        if (event.key === 'Escape' && editing) {
          handleCancelEdit();
        }
        if (event.key === 'Enter') {
          handleEditClick();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [editing, selectedCellId]);

  useEffect(() => {
    if (message && message.action_messages){
      const messageLength = message.action_messages.length;
      // Make sure that both model and kali_env are received
      if (messageLength % 2 !== 0) {
        return;
      }
      setDisplayedIndex(messageLength / 2);
    }
  }, [message]);

  useEffect(() => {
    setDisplayedIndex(1);
  }, [phaseDisplayedIndex]);

  if (!message) return null;

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = () => {
    setEditing(true);
    onEditingChange(true);
    setEditedMessage(message.message || '');
  };

  const handleToggleVersion = (num) => {
    if (onPhaseChildUpdate) {
        onPhaseChildUpdate(message.agent_id, num); // Notify parent of the update
    }
  };

  const handleSaveClick = async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(message.current_id, editedMessage);
      setEditing(false);
      onEditingChange(false);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
    onEditingChange(false);
    setEditedMessage(message.message || '');
  };

  const handleContainerClick = (e) => {
    e.stopPropagation();
    onCellSelect(message.current_id);
  };

  const handleChildUpdate = (num) => {
      setDisplayedIndex((prev) => prev + num);
  };

  return (
    <Box className={`agent-message-container ${selectedCellId === message.current_id ? 'selected' : ''}`}
      onClick={handleContainerClick}
    >
      <Card className="message-bubble agent-bubble">
        <CardContent>
          <Box className="agent-message-header">
            <Typography className="agent-name">Agent: {message.agent_id}</Typography>
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
                    <TextField
                      multiline
                      fullWidth
                      minRows={3}
                      maxRows={10}
                      value={editedMessage}
                      onChange={(e) => setEditedMessage(e.target.value)}
                      className="edit-textarea"
                    />
                    <Box className="agent-message-actions">
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSaveClick}
                        size="small"
                        className="save-button"
                        sx={{ mr: 1 }}
                      >
                        <SaveIcon/>
                      </Button>
                      <Button
                        variant="outlined"
                        color="secondary"
                        onClick={handleCancelEdit}
                        size="small"
                        className="cancel-button"
                      >
                        <CloseIcon/>
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
                        {message.message || ''}
                      </Typography>
                    </Card>
                    <Box className="agent-message-actions">
                      <Button
                        variant="outlined"
                        color="primary"
                        onClick={handleEditClick}
                        size="small"
                        className="edit-button"
                      >
                        <EditIcon />
                      </Button>

                      {/* Toggle Version Arrows */}
                    {phaseVersionLength > 1 && (
                    <>
                    <Typography variant="caption" sx={{ mx: 1 }}>
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      {/* Arrow Buttons */}
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <IconButton
                          aria-label="arrow back"
                          onClick={() => handleToggleVersion(-1)}
                          disabled={phaseDisplayedIndex === 1}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowBackIcon />
                        </IconButton>
                        <IconButton
                          aria-label="arrow forward"
                          onClick={() => handleToggleVersion(1)}
                          disabled={phaseDisplayedIndex === phaseVersionLength}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowForwardIcon />
                        </IconButton>
                      </Box>

                      {/* Version Number */}
                      <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                        {phaseDisplayedIndex}/{phaseVersionLength}
                      </Typography>
                    </Box>
                    </>)}     

                    </Box>
                  </Box>
                )}
              </Box>
            ) : (
              <Box className="action-messages-container">
                {message.action_messages.slice(2*displayedIndex-2, 2*displayedIndex).map((actionMessage, index) => (
                  <div ref={(el) => (cellRefs.current[actionMessage.current_id] = el)} key={actionMessage.current_id}>
                    <ActionMessage
                      key={index}
                      index={index}
                      action={actionMessage}
                      onUpdateActionInput={onUpdateActionInput}
                      onRerunAction={onRerunAction}
                      onEditingChange={onEditingChange}
                      isEditing={isEditing}                    
                      selectedCellId={selectedCellId}
                      onCellSelect={onCellSelect}
                      onChildUpdate={handleChildUpdate}
                      displayedIndex={displayedIndex}
                      versionLength={message.action_messages.length / 2}
                    />
                  </div>
                ))}
              </Box>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AgentMessage;