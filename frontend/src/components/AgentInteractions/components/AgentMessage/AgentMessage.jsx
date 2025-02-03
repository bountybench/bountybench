import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

const AgentMessage = ({ message, onUpdateActionInput, onRerunAction, onEditingChange, isEditing, selectedCellId, onCellSelect, cellRefs }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editedMessage, setEditedMessage] = useState(message.message || '');
  const textFieldRef = useRef(null);

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = (e) => {
    e.stopPropagation();
    onEditingChange(true);
    setEditedMessage(message.message || '');
  };

  const handleSaveClick = async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(message.current_id, editedMessage);
      onEditingChange(false);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  };

  const handleCancelEdit = () => {
    onEditingChange(false);
    setEditedMessage(message.message || '');
  };

  const handleContainerClick = (e) => {
    e.stopPropagation();
    if (message.current_children && message.current_children.length > 0) {
      // If there are action messages, select the first action message instead
      const firstActionMessageId = message.current_children[0].current_id;
      onCellSelect(firstActionMessageId);
    } else {
      // If no action messages, allow selecting the agent message
      onCellSelect(message.current_id);
    }
    // setEditing(false);
    // onEditingChange(false);
    
    // // Enter edit mode if clicking text content
    // if (e.target.closest('.agent-message-text-card')) {
    //   setEditing(true);
    //   onEditingChange(false);
    // }
  };

  // Synchronize state when entering editing mode
  useEffect(() => {
    if (isEditing && selectedCellId === message.current_id) {
      setEditedMessage(message.message || '');
      if (textFieldRef.current) {
        setTimeout(() => {
          textFieldRef.current.focus();   // Focus the text field when editing starts
          textFieldRef.current.setSelectionRange(0, 0); // Set cursor at the start
        }, 0);
      }
    }
  }, [isEditing, selectedCellId]);
  
  return (
    <Box 
      className={`agent-message-container ${selectedCellId === message.current_id ? 'selected' : ''}`}
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
                {isEditing && selectedCellId === message.current_id ? (
                  <Box className="edit-mode-container">
                    <TextField
                      inputRef={textFieldRef}
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
                        sx={{ display: isEditing && selectedCellId !== message.current_id ? 'none' : 'flex' }}
                      >
                        <EditIcon />
                      </Button>
                    </Box>
                  </Box>
                )}
              </Box>
            ) : (
              <Box className="action-messages-container">
                <Typography className="action-messages-title">Actions:</Typography>
                {message.current_children.map((actionMessage, index) => (
                  <div ref={(el) => (cellRefs.current[actionMessage.current_id] = el)} key={actionMessage.current_id}>
                    <ActionMessage 
                    key={actionMessage.current_id}
                    action={actionMessage} 
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    selectedCellId={selectedCellId}
                    onCellSelect={onCellSelect}
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