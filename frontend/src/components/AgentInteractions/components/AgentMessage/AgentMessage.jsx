import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

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
    <Box className="agent-message-container">
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
                      >
                        <SaveIcon/>
                      </Button>
                    </Box>
                  </Box>
                ) : (
                  <>
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
                    </Box>
                  </>
                )}
              </Box>
            ) : (
              <Box className="action-messages-container">
                {/* <Typography className="action-messages-title">Actions:</Typography> */}
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