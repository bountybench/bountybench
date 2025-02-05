import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import { formatData } from '../../utils/messageFormatters';
import './ActionMessage.css'

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const ActionMessage = ({ index, action, onUpdateActionInput, onRerunAction, onEditingChange, isEditing, selectedCellId, onCellSelect, onChildUpdate, displayedIndex, versionLength }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState('');
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (selectedCellId === action.current_id) {
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

  const originalMessageContent = formatData(action.message);

  const handleEditClick = () => {
    setEditing(true);
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
      setEditing(false);
      onEditingChange(false);
    } catch (error) {
      console.error('Error updating action message:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
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
          <Box className="edit-mode-container">
            <Typography variant="caption" color="text.secondary">
              Editing Message:
            </Typography>
            <TextField
              multiline
              minRows={3}
              maxRows={10}
              value={editedMessage}
              onChange={(e) => setEditedMessage(e.target.value)}
              className="edit-textarea"
              fullWidth
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
            <Box className="action-message-buttons">
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
                  </>)}               
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