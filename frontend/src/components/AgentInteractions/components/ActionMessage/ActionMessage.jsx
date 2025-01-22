import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ReplayIcon from '@mui/icons-material/Replay';
import { formatData } from '../../utils/messageFormatters';

const ActionMessage = ({ action, onUpdateActionInput, onRerunAction }) => {
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
    } catch (error) {
      console.error('Error updating action message:', error);
    }
  };

  const handleExpandClick = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <Card className="action-message" variant="outlined" sx={{ mt: 2 }}>
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
              <Box mt={1}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Message:
                </Typography>
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
                    {originalMessageContent}
                  </Typography>
                </Card>
              </Box>
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
                  Metadata
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
                      {JSON.stringify(action.additional_metadata, null, 2)} </Typography>
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

export default ActionMessage;