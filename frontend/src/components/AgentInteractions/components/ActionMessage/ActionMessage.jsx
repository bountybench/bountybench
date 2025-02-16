import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import { formatData } from '../../utils/messageFormatters';
import { CopyButton } from '../buttons/CopyButton';
import './ActionMessage.css';

const ActionMessage = ({ action, onUpdateMessageInput, onRunMessage, onEditingChange, isEditing, selectedCellId, onCellSelect }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(action?.message || '');
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const [originalMessageContent, setOriginalMessageContent] = useState(formatData(action?.message || ''));

  const handleCopyClick = () => {
    const message = formatData(editedMessage)
		navigator.clipboard.writeText(message);
	};

  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    onEditingChange(false);
    setEditedMessage(originalMessageContent);
  }, [originalMessageContent, onEditingChange]);
  
  const handleEditClick = useCallback(() => {
    setEditing(true);
    onEditingChange(true);
    setEditedMessage(originalMessageContent);
  }, [originalMessageContent, onEditingChange]);

  const handleSaveClick = useCallback(async () => {
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      setOriginalMessageContent(editedMessage);
      setEditing(false);
      onEditingChange(false);
      await onUpdateMessageInput(action.current_id, editedMessage);
    } catch (error) {
      console.error('Error updating action message:', error);
    }
  }, [action, editedMessage, onEditingChange, onUpdateMessageInput]);

  const handleRunClick = useCallback(async () => {
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onRunMessage(action.current_id);
    } catch (error) {
      console.error('Error running action:', error);
    }
  }, [action, onRunMessage]);

  const textFieldRef = useRef(null);

  useEffect(() => {
    setOriginalMessageContent(action.message);
  }, [action]);

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
      if (selectedCellId === action.current_id) {
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
  }, [editing, action, handleCancelEdit, handleEditClick, handleSaveClick, handleRunClick, selectedCellId]);

  if (!action) return null;
  
  const handleToggleMetadata = (event) => {
    event.stopPropagation();
    setMetadataExpanded(!metadataExpanded);
  };

  const handleExpandClick = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  const handleContainerClick = (e) => {
    e.stopPropagation();
    onCellSelect(action.current_id);
  };




  return (
    <Card 
      className={`action-message ${action.resource_id ? action.resource_id.toUpperCase() : ''} ${selectedCellId === action.current_id ? 'selected' : ''}`}
      onClick={handleContainerClick}
      variant="outlined"
    >
      <CardContent>
        <Box className="action-message-header">
          <Box>
            <Typography className="action-message-title">
              {action.resource_id ? action.resource_id.toUpperCase() : 'ACTION'}
            </Typography>
            {action.timestamp && (
              <Typography className="message-timestamp">
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
          {editing ? (
            <>
              <Box className="editing-message-content">
                <TextField className="action-message-text message-edit-field"
                  inputRef={textFieldRef}
                  multiline
                  minRows={3}
                  maxRows={10}
                  value={editedMessage}
                  onChange={(e) => setEditedMessage(e.target.value)}
                  fullWidth
                />
              </Box>
              <Box className="message-buttons" sx={{ display: 'flex' }}>
            <CopyButton onClick={handleCopyClick} />
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
            </>
          ) : (
            <>
              <Box className="action-message-content">
                <Typography className="action-message-text">
                  {originalMessageContent}
                </Typography>
              </Box>
              <Box className="message-buttons" sx={{ display: 'flex' }}>
            <CopyButton onClick={handleCopyClick} />
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