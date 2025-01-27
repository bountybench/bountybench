import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const AgentMessage = ({ message, onUpdateActionInput, onRerunAction, onPhaseChildUpdate, phaseMultiVersion, phaseDisplayedIndex, phaseVersionLength }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message.message || '');

  const [displayedIndex, setDisplayedIndex] = useState(1);
  const [multiVersion, setMultiVersion] = useState(false);

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = () => {
    setEditing(true);
    setEditedMessage(message.message || '');
  };

  useEffect(() => {
    if (message.action_messages){
      const messageLength = message.action_messages.length;
      // Make sure that both model and kali_env are received
      if (messageLength % 2 !== 0) {
        return;
      }
      setMultiVersion(true);
      setDisplayedIndex(messageLength / 2);
    }
  }, [message, message.action_messages]);

  const handleToggleVersion = (num) => {
    if (onPhaseChildUpdate) {
        onPhaseChildUpdate(num); // Notify parent of the update
    }
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

  const handleChildUpdate = (num) => {
      setDisplayedIndex((prev) => prev + num);
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
                      >
                        <EditIcon />
                      </Button>

                      {/* Toggle Version Arrows */}
                    {phaseMultiVersion && (
                    <>
                    <Typography variant="caption" sx={{ mx: 1 }}>
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      {/* Arrow Buttons */}
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <IconButton
                          onClick={() => handleToggleVersion(-1)}
                          disabled={phaseDisplayedIndex === 1}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowBackIcon />
                        </IconButton>
                        <IconButton
                          onClick={() => handleToggleVersion(1)}
                          disabled={phaseDisplayedIndex === phaseVersionLength}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowForwardIcon />
                        </IconButton>
                      </Box>

                      {/* Version Number */}
                      <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                        {phaseDisplayedIndex}/{phaseVersionLength}
                      </Typography>
                    </Box>
                    </>)}     

                    </Box>
                  </Box>
                )}
              </Box>
            ) : (
              <Box className="action-messages-container">
                {message.action_messages.slice(2*displayedIndex-2, 2*displayedIndex).map((actionMessage, index) => (
                  <ActionMessage
                    key={index}
                    action={actionMessage}
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                    onChildUpdate={handleChildUpdate}
                    multiVersion={multiVersion}
                    displayedIndex={displayedIndex}
                    versionLength={message.action_messages.length / 2}
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