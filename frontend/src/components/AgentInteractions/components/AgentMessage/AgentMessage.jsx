import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

const AgentMessage = ({ message, onUpdateActionInput, isNextDisabled, onEditingChange, isEditing, selectedCellId, onCellSelect, cellRefs }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editedMessage, setEditedMessage] = useState(message.message || '');
  const textFieldRef = useRef(null);

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = (e) => {
    e.stopPropagation();
    onEditingChange(true);
    setEditedMessage(message.message || '');
  };

  const handleKeyDown = (e) => {
    if (!isEditing) return;  // Prevent handling if not editing

    if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault(); // Prevent the default behavior of Enter key
      if (e.shiftKey || (e.ctrlKey || e.metaKey)) {
        console.log("Saving message");
        handleSaveClick();  // Save on Shift + Enter or Ctrl/Cmd + Enter
      }
    }
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
                      onKeyDown={handleKeyDown}
                    />
                    <Box className="message-actions">
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleCancelEdit}
                        size="small"
                        className="cancel-button"
                        sx={{ display: isNextDisabled ? 'none' : 'flex' }}
                      >
                        <CloseIcon/>
                      </Button>
                      <Button
                        variant="contained"
                        color="secondary"
                        onClick={handleSaveClick}
                        size="small"
                        className="save-button"
                      sx={{ display: isNextDisabled ? 'none' : 'flex' }}
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
                        {message.message || ''}
                      </Typography>
                    </Card>
                    {selectedCellId === message.current_id && (
                      <Box className="message-actions">
                          <Button
                            variant="outlined"
                            color="primary"
                            onClick={handleEditClick}
                            size="small"
                            className="edit-button"
                            sx={{ display: isNextDisabled ? 'none' : 'flex' }}
                          >
                            <EditIcon />
                          </Button>
                          <Button
                            variant="outlined"
                            onClick={handleSaveClick}
                            size="small"
                            className="save-button hovering"
                            sx={{ display: isNextDisabled ? 'none' : 'flex' }}
                          >
                            <KeyboardArrowRightIcon/>
                          </Button>
                      </Box>
                      )
                    }
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
                    isNextDisabled={isNextDisabled}
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