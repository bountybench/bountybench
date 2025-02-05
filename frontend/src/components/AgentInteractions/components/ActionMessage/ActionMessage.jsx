import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import { formatData } from '../../utils/messageFormatters';
import './ActionMessage.css';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const ActionMessage = ({ index, action, onUpdateMessageInput, onRerunMessage, onEditingChange, isEditing, selectedCellId, onCellSelect, onChildUpdate, displayedIndex, versionLength }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(action.message || '');
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const [originalMessageContent, setOriginalMessageContent] = useState(formatData(action.message));

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

  const handleRerunClick = useCallback(async () => {
    if (!action.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onRerunMessage(action.current_id);
    } catch (error) {
      console.error('Error rerunning action:', error);
    }
  }, [action, onRerunMessage]);

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
            handleRerunClick();
          }
        }
        else if (event.key === 'Enter' && !event.altKey) {
          handleEditClick();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [editing, action, handleCancelEdit, handleEditClick, handleSaveClick, handleRerunClick, onUpdateMessageInput, selectedCellId]);

  if (!action) return null;
  
  const handleToggleMetadata = (event) => {
    event.stopPropagation();
    setMetadataExpanded(!metadataExpanded);
  };

  const handleToggleVersion = (num) => {
    if (onChildUpdate) {
      onChildUpdate(num); // Notify parent of the update
    }
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
        </>
        ) : (
          <>
            <Box className="action-message-content">
              <Typography className="action-message-text">
                {originalMessageContent}
              </Typography>
            </Box>
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
                onClick={handleRerunClick}
                size="small"
                aria-label="rerun"
                className="rerun-button"
              >
                <KeyboardArrowRightIcon />
              </Button>

                  {/* Toggle Version Arrows */}
                  { versionLength > 1 && index === 0 && (
                  <>
                    <Typography variant="caption" sx={{ mx: 1 }}>
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      {/* Arrow Buttons */}
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <IconButton
                          aria-label="arrow back"
                          onClick={() => handleToggleVersion(-1)}
                          disabled={displayedIndex === 1}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowBackIcon />
                        </IconButton>
                        <IconButton
                          aria-label="arrow forward"
                          onClick={() => handleToggleVersion(1)}
                          disabled={displayedIndex === versionLength}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowForwardIcon />
                        </IconButton>
                      </Box>

                      {/* Version Number */}
                      <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                        {displayedIndex}/{versionLength}
                      </Typography>
                    </Box>
                  </>
                )}               
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