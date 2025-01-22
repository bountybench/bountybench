import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ActionMessage from './ActionMessage';

const AgentMessage = ({ message, onUpdateActionInput, onRerunAction }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message.message || '');

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = () => {
    setEditing(true);
    setEditedMessage(message.message || '');
  };

  const handleSaveClick = async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      await onUpdateActionInput(message.current_id, editedMessage);
      setEditing(false);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  };

  return (
    <Box className={`message-container ${message.agent_id}`}>
      <Card 
        className="message-bubble agent-bubble"
        sx={{
          backgroundColor: '#f0f4f8 !important',
          '& .MuiCardContent-root': {
            backgroundColor: '#f0f4f8 !important'
          },
          '& .action-bubble': {
            boxShadow: 1,
          },
          p: 2,
          mt: 2
        }}
      >
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1">Agent: {message.agent_id}</Typography>
            <IconButton size="small" onClick={handleToggleAgentMessage}>
              {agentMessageExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          <Collapse in={agentMessageExpanded}>
            <Box mt={1}>
              {editing ? (
                <Box>
                  <TextField
                    multiline
                    fullWidth
                    minRows={3}
                    maxRows={10}
                    value={editedMessage}
                    onChange={(e) => setEditedMessage(e.target.value)}
                    sx={{
                      '& .MuiInputBase-input': {
                        color: 'black',
                      },
                    }}
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
                  <Card 
                    variant="outlined" 
                    sx={{ 
                      bgcolor: '#e5e9f0 !important',
                      '& .MuiCardContent-root': {
                        backgroundColor: '#e5e9f0 !important'
                      },
                      p: 1 
                    }}
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
                      {message.message || ''}
                    </Typography>
                  </Card>
                  <Box mt={1} display="flex" justifyContent="flex-end">
                    <Button
                      variant="outlined"
                      color="primary"
                      onClick={handleEditClick}
                      size="small"
                    >
                      <EditIcon />
                    </Button>
                  </Box>
                </>
              )}
            </Box>

            {message.current_children && message.current_children.length > 0 && (
              <Box mt={2}>
                <Typography variant="subtitle2">Actions:</Typography>
                {message.current_children.map((actionMessage, index) => (
                  <ActionMessage
                    key={index}
                    action={actionMessage}
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                  />
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