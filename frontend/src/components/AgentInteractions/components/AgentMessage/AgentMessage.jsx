import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, Card, CardContent, IconButton, TextField, Button, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import ActionMessage from '../ActionMessage/ActionMessage';
import { formatData, formatTimeElapsed } from '../../utils/messageFormatters';
import './AgentMessage.css';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { CopyButton } from '../buttons/CopyButton';

const AgentMessage = ({
  index,
  message,
  onUpdateMessageInput,
  onRunMessage,
  onEditingChange,
  isEditing,
  selectedCellId,
  onCellSelect,
  onToggleVersion,
  registerMessageRef,
  registerToggleOperation,
  parentMessage
}) => {
  const [agentMessageExpanded, setAgentMessageExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedMessage, setEditedMessage] = useState(message?.message || '');
  const textFieldRef = useRef(null);

  const [originalMessageContent, setOriginalMessageContent] = useState(formatData(message?.message || ''));

  const messageRef = useRef(null);

  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    onEditingChange(false);
    setEditedMessage(originalMessageContent);
  }, [originalMessageContent, onEditingChange]);

  const handleEditClick = useCallback(() => {
    if (!message?.current_children || message?.current_children.length === 0) {
      setEditing(true);
      onEditingChange(true);
      setEditedMessage(originalMessageContent);
    }
  }, [originalMessageContent, onEditingChange, message]);

  const handleCopyClick = () => {
    const formattedMessage = formatData(editedMessage);
    if (formattedMessage === "") {
      return
    }

    navigator.clipboard.writeText(formattedMessage);
  }

  const handleSaveClick = useCallback(async () => {
    if (!message.current_id) {
      console.error('Message id is undefined');
      return;
    }
    try {
      setOriginalMessageContent(editedMessage);
      setEditing(false);
      onEditingChange(false);
      await onUpdateMessageInput(message.current_id, editedMessage);
    } catch (error) {
      console.error('Error updating message:', error);
    }
  }, [message, editedMessage, onEditingChange, onUpdateMessageInput]);

  const handleRunClick = useCallback(async () => {
    if (!message.current_id) {
      console.error('Action id is undefined');
      return;
    }
    try {
      await onRunMessage(message.current_id);
    } catch (error) {
      console.error('Error running action:', error);
    }
  }, [message, onRunMessage]);

  const handleMoveUp = useCallback(() => {
    setTimeout(() => {
      if (index > 0) {
        onCellSelect(parentMessage.current_children[index - 1].current_id);
      }
    }, 0);
  }, [onCellSelect]);

  const handleMoveLeft = useCallback(() => {
    setTimeout(() => {
      onCellSelect(parentMessage.current_id);
    }, 0);
  }, [onCellSelect]);

  const handleMoveDown = useCallback(() => {
    setTimeout(() => {
      if (index < parentMessage.current_children.length - 1) {
        onCellSelect(parentMessage.current_children[index + 1].current_id);
      }
    }, 0);
  }, [onCellSelect, parentMessage]); // parentMessage might append more children

  const handleMoveRight = useCallback(() => {
    setTimeout(() => {
      if (message.current_children.length > 0) {
        onCellSelect(message.current_children[0].current_id);
      }
    }, 0);
  }, [onCellSelect]);

  useEffect(() => {
    setOriginalMessageContent(message?.message);
  }, [message]);

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

  const navigationActions = {
    'ArrowUp': handleMoveUp,
    'w': handleMoveUp,
    'ArrowLeft': handleMoveLeft,
    'a': handleMoveLeft,
    'ArrowDown': handleMoveDown,
    's': handleMoveDown,
    'ArrowRight': handleMoveRight,
    'd': handleMoveRight,
  };
  
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (selectedCellId === message?.current_id) {
        if (event.key === 'Escape' && editing) {
          handleCancelEdit();
        }
        else if (event.shiftKey && event.key === 'Enter') {
          event.preventDefault();
          if (editing) {
            handleSaveClick();      // Call the save function
          } else {
            handleRunClick();
          }
        }
        else if (event.key === 'Enter' && !event.altKey && !editing) {
          handleEditClick();
        }
        else if (event.key in navigationActions && !editing) {
          event.preventDefault();
          navigationActions[event.key]();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [editing, message, handleCancelEdit, handleEditClick, handleSaveClick, handleRunClick, selectedCellId]);

  useEffect(() => {
    if (selectedCellId === message.current_id && messageRef.current && 
      typeof messageRef.current.scrollIntoView === 'function') {
      messageRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [selectedCellId]);

  const handlePrevVersion = () => {
    if (message?.version_prev) {
      registerToggleOperation(message.current_id, message.version_prev, 'prev');
      onToggleVersion(message.current_id, 'prev');
    }
  };

  const handleNextVersion = () => {
    if (message?.version_next) {
      registerToggleOperation(message.current_id, message.version_next, 'next');
      onToggleVersion(message.current_id, 'next');
    }
  };

  if (!message) return null;

  const handleToggleAgentMessage = () => setAgentMessageExpanded(!agentMessageExpanded);

  const handleContainerClick = (e) => {
    e.stopPropagation();
    onCellSelect(message.current_id);
  };

  const getMessageButtons = () => {
    if (editing) {
      return (
        <Box className="message-buttons">
          <CopyButton onClick={handleCopyClick} />
          <Button
            variant="outlined"
            color="secondary"
            onClick={handleCancelEdit}
            size="small"
            aria-label="cancel"
            className="cancel-button"
          >
            <CloseIcon />
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
            <KeyboardArrowRightIcon />
          </Button>
        </Box>
      );
    } else {
      return (
        <Box className="message-buttons">
          <>
            {(!message.current_children || message.current_children.length === 0) && (
              <>
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
              </>
            )}
          </>
          <>
            <Typography variant="caption" sx={{ mx: 1 }} />
            {(message?.version_next || message?.version_prev) && message.versions && (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {/* Arrow Buttons */}
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <IconButton
                    aria-label="arrow back"
                    disabled={!message?.version_prev}
                    sx={{ color: 'black' }}
                    size="small"
                    onClick={handlePrevVersion}
                  >
                    <ArrowBackIcon />
                  </IconButton>
                  {/* Version Number */}
                  {message.versions && (
                    <Typography variant="caption" sx={{ mt: 0.5, fontWeight: 'bold', color: 'black' }}>
                      {message.versions.indexOf(message.current_id) + 1}/{message.versions.length}
                    </Typography>
                  )}
                  <IconButton
                    aria-label="arrow forward"
                    disabled={!message?.version_next}
                    sx={{ color: 'black' }}
                    size="small"
                    onClick={handleNextVersion}
                  >
                    <ArrowForwardIcon />
                  </IconButton>
                </Box>
              </Box>
            )}
          </>
        </Box>
      );
    }
  }

  return (
    <Box
      className={`agent-message-container ${selectedCellId === message.current_id ? 'selected' : ''}`}
      onClick={handleContainerClick}
      ref={messageRef}
      id={`message-${message.current_id}`}
      data-message-id={message.current_id}
    >
      <Card className="message-bubble agent-bubble">
        <CardContent>
          <Box className="agent-message-header">
            <Box className="agent-title">
              <Typography className="agent-name">{message.agent_id.toUpperCase()}</Typography>
              {message.agent_id.toUpperCase() !== 'SYSTEM' && Number.isInteger(message.iteration) && message.iteration >= 0 && (
                <Typography className="message-timestamp">
                  Iteration {message.iteration}  |
                </Typography>
              )}
              {message.timestamp && (
                <Typography className="message-timestamp">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </Typography>
              )}
              {message.iteration_time_ms && (
                <Typography className="message-timestamp">
                  | {formatTimeElapsed(message.iteration_time_ms) || '-'} elapsed
                </Typography>
              )}
            </Box>
            <IconButton
              size="small"
              onClick={handleToggleAgentMessage}
              className="agent-toggle-button"
            >
              {agentMessageExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          <Collapse in={agentMessageExpanded}>
            {(originalMessageContent && originalMessageContent.trim() !== '') && (
              <Box className="agent-message-content">
                {editing ? (
                  <Box className="edit-mode-container">
                    <TextField className="agent-message-text message-edit-field"
                      inputRef={textFieldRef}
                      multiline
                      fullWidth
                      minRows={3}
                      value={editedMessage}
                      onChange={(e) => setEditedMessage(e.target.value)}
                    />
                  </Box>
                ) : (
                  <Box className="display-mode-container">
                    <Card className="agent-message-text-card">
                      <Typography
                        component="pre"
                        className="agent-message-text"
                      >
                        {originalMessageContent}
                      </Typography>
                    </Card>
                  </Box>
                )}
              </Box>
            )}

            {message.current_children && message.current_children.length > 0 && (
              <Box className="action-messages-container">
                {message.current_children.map((actionMessage, index) => (
                  <ActionMessage
                    key={actionMessage.current_id}
                    index={index}
                    action={actionMessage}
                    onUpdateMessageInput={onUpdateMessageInput}
                    onRunMessage={onRunMessage}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    selectedCellId={selectedCellId}
                    onCellSelect={onCellSelect}
                    registerMessageRef={registerMessageRef}
                    registerToggleOperation={registerToggleOperation}
                    parentMessage={message}
                  />
                ))}
              </Box>
            )}

            {getMessageButtons()}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AgentMessage;