import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import ReplayIcon from '@mui/icons-material/Replay';
import { formatData } from '../../utils/messageFormatters';
import './ActionMessage.css'

const ActionMessage = ({ action, onUpdateActionInput, onEditingChange, isEditing, selectedCellId, onCellSelect }) => {
  const [expanded, setExpanded] = useState(true);
  const [editedMessage, setEditedMessage] = useState(action.message || '');
  const [metadataExpanded, setMetadataExpanded] = useState(false);
  const textFieldRef = useRef(null);

  
  // Synchronize state when entering editing mode
  useEffect(() => {
    if (isEditing && selectedCellId === action.current_id) {
      setEditedMessage(action.message || '');
      if (textFieldRef.current) {
        setTimeout(() => {
          textFieldRef.current.focus();   // Focus the text field when editing starts
          textFieldRef.current.setSelectionRange(0, 0); // Set cursor at the start
        }, 0);
      }
    }
  }, [isEditing, selectedCellId]);
  
  if (!action) return null;

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
  
  const handleToggleMetadata = (event) => {
    event.stopPropagation();
    setMetadataExpanded(!metadataExpanded);
  };

  const originalMessageContent = formatData(action.message);

  const handleEditClick = (e) => {
    e.stopPropagation();
    onEditingChange(true);
    setEditedMessage(originalMessageContent);
  };

  const handleSaveClick = async () => {
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(action.current_id, editedMessage);
      onEditingChange(false);
    } catch (error) {
      console.error('Error updating action message:', error);
    }
  };

  const handleCancelEdit = () => {
    onEditingChange(false);
    setEditedMessage(originalMessageContent);
  };

  const handleExpandClick = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };
  
  const handleContainerClick = (e) => {
    e.stopPropagation();
    onCellSelect(action.current_id);
    // setEditing(false);
    // onEditingChange(false);
    
    // // Enter edit mode if clicking text content
    // if (e.target.closest('.action-message-text')) {
    //   setEditing(true);
    //   onEditingChange(true);
    // }
  };

  return (
    <Card 
      className={`action-message ${action.resource_id ? action.resource_id.toUpperCase() : ''} ${selectedCellId === action.current_id ? 'selected' : ''}`}
      variant="outlined"
      onClick={handleContainerClick}
    >
    <CardContent>
      <Box className="action-message-header">
        <Box>
          <Typography className="action-message-title">
            {action.resource_id ? action.resource_id.toUpperCase() : 'ACTION'}
          </Typography>
          {action.timestamp && (
            <Typography className="action-message-timestamp">
              {new Date(action.timestamp).toLocaleTimeString()}
            </Typography>
          )}
        </Box>
        <IconButton
          onClick={handleExpandClick}
          aria-expanded={expanded}
          aria-label="show more"
          className="action-toggle-button"
        >
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        {isEditing && selectedCellId === action.current_id ? (
          <Box className="edit-mode-container">
            <Typography variant="caption" color="text.secondary">
              Editing Message:
            </Typography>
            <TextField
              inputRef={textFieldRef}
              multiline
              minRows={3}
              maxRows={10}
              value={editedMessage}
              onChange={(e) => setEditedMessage(e.target.value)}
              className="edit-textarea"
              fullWidth
              onKeyDown={handleKeyDown}
            />
            <Box className="action-message-buttons">
              <Button
                variant="contained"
                color="primary"
                onClick={handleSaveClick}
                size="small"
                aria-label="save"
                sx={{ mr: 1 }}
              >
                <SaveIcon/>
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleCancelEdit}
                size="small"
                aria-label="cancel"
              >
                <CloseIcon/>
              </Button>
            </Box>
          </Box>
        ) : (
          <>
            <Box className="action-message-content">
              <Typography className="action-message-text">
                {originalMessageContent}
              </Typography>
            </Box>
            <Box className="action-message-buttons" sx={{ display: isEditing && selectedCellId !== action.current_id ? 'none' : 'flex' }}>
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
            </Box>
          </>
        )}

        {/* Metadata section */}
        {action.additional_metadata && (
          <Box className="metadata-section">
            <Box 
              className="metadata-toggle"
              onClick={handleToggleMetadata}
            >
              <Typography className="metadata-label">
                Metadata
                <IconButton size="small" className="action-toggle-button">
                  {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                </IconButton>
              </Typography>
            </Box>
            
            <Collapse in={metadataExpanded}>
              <Box className="metadata-content">
                <Typography className="metadata-text">
                  {JSON.stringify(action.additional_metadata, null, 2)}
                </Typography>
              </Box>
            </Collapse>
          </Box>
        )}
      </Collapse>
    </CardContent>
    </Card>
  );
};

export default ActionMessage;