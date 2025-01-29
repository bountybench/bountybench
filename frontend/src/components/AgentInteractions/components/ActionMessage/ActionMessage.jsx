import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ReplayIcon from '@mui/icons-material/Replay';
import { formatData } from '../../utils/messageFormatters';
import './ActionMessage.css'

const ActionMessage = ({ action, onUpdateActionInput, onRerunAction, onEditingChange, isEditing }) => {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState('');
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  if (!action) return null;

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

  const handleExpandClick = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <Card 
      className={`action-message ${action.resource_id ? action.resource_id.toUpperCase() : ''}`} 
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
              >
                <SaveIcon/>
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
                disabled={isEditing && !editing}
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
                <ReplayIcon />
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