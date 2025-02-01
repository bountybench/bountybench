import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import ActionMessage from '../ActionMessage/ActionMessage';
import './AgentMessage.css'

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const AgentMessage = ({ index, message, onUpdateActionInput, onRerunAction, onEditingChange, isEditing, onPhaseChildUpdate, phaseDisplayedIndex, phaseVersionLength }) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message.message || '');

  const [displayedIndex, setDisplayedIndex] = useState(1);
  // const [multiVersion, setMultiVersion] = useState(false);
  const [versionChain, setVersionChain] = useState([message.current_children]);
    
  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleEditClick = () => {
    setEditing(true);
    onEditingChange(true);
    setEditedMessage(message.message || '');
  };

  const getActionIds = (actions) => actions.length === 0 ? [] : actions.map(action => action.current_id);
  const arraysEqual = (arr1, arr2) => JSON.stringify(arr1) === JSON.stringify(arr2);

  useEffect(() => {
      if (message.action_messages){
        const curr_children = message.current_children;
        const versionLength = versionChain.length;
        const curr_children_ids = getActionIds(curr_children);
        const all_action_ids = getActionIds(message.action_messages);
        if (arraysEqual(all_action_ids,curr_children_ids)){
          setVersionChain([curr_children]);
          return;
        }
        // when current children is not equal to latest version
        const last_version_ids = getActionIds(versionChain[versionLength-1]);
        if (!arraysEqual(last_version_ids,curr_children_ids)) {
          // if all of current children is new, we have a new version
          if (curr_children_ids.filter(child => last_version_ids.includes(child)).length === 0){
            setVersionChain((prev) => {
              const newVersionChain = [...prev, curr_children];
              setDisplayedIndex(newVersionChain.length); // Uses the updated versionChain
              return newVersionChain;
            });
          }
          else{
            const newChildren = curr_children.filter(child => !last_version_ids.includes(child.current_id));
            setVersionChain(prev => prev.map((innerList, index) => 
                index === displayedIndex - 1 ? [...innerList, ...newChildren] : innerList
              ));
          }
        }
      }
    }, [message, message.action_messages]);

    useEffect(() => {
      setDisplayedIndex(1);
    }, [phaseDisplayedIndex]);

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
      onEditingChange(false);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
    onEditingChange(false);
    setEditedMessage(message.message || '');
  };

  useEffect(() => {
    const handleEscKey = (event) => {
      if (event.key === 'Escape' && editing) {
        handleCancelEdit();
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => {
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [editing]);

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
                        sx={{ mr: 1 }}
                      >
                        <SaveIcon/>
                      </Button>
                      <Button
                        variant="outlined"
                        color="secondary"
                        onClick={handleCancelEdit}
                        size="small"
                        className="cancel-button"
                      >
                        <CloseIcon/>
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
                        sx={{ display: isEditing && !editing ? 'none' : 'flex' }}
                      >
                        <EditIcon />
                      </Button>

                      {/* Toggle Version Arrows */}
                    {phaseVersionLength > 1 && index === 0 && (
                    <>
                    <Typography variant="caption" sx={{ mx: 1 }}>
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      {/* Arrow Buttons */}
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <IconButton
                          aria-label="arrow back"
                          onClick={() => handleToggleVersion(-1)}
                          disabled={phaseDisplayedIndex === 1}
                          sx={{ color: 'black' }}
                          size="small"
                        >
                          <ArrowBackIcon />
                        </IconButton>
                        <IconButton
                          aria-label="arrow forward"
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
                {versionChain[displayedIndex - 1].map((actionMessage, index) => (
                  <ActionMessage
                    key={index}
                    index={index}
                    action={actionMessage}
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    onChildUpdate={handleChildUpdate}
                    displayedIndex={displayedIndex}
                    versionLength={versionChain.length}
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