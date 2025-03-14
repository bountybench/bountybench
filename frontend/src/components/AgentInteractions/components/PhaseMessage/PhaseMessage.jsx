import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({
  message,
  onUpdateMessageInput,
  onRunMessage,
  onEditingChange,
  isEditing,
  selectedCellId,
  onCellSelect,
  onToggleVersion,
  registerMessageRef,
  registerToggleOperation // Add this new prop
}) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);
  const messageContainerRef = useRef(null);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  // Register this component's ref with parent
  useEffect(() => {
    if (messageContainerRef.current && message.current_id) {
      registerMessageRef(message.current_id, messageContainerRef.current);
    }
  }, [message.current_id, registerMessageRef]);

  return (
    <Box
      className="message-container phase"
      ref={messageContainerRef}
    >
      <Card className="message-bubble phase-bubble">
        <CardContent>
          <Box className="phase-header">
            <Typography className="phase-title">
              Phase: {message.phase_name}
            </Typography>
            <IconButton
              size="small"
              onClick={handleToggleContent}
              className="phase-toggle-button"
              aria-label="toggle phase content"
            >
              {contentExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={contentExpanded}>
            <Typography className="phase-summary">
              Summary: {message.phase_summary || '(no summary)'}
            </Typography>

            {message.current_children?.length > 0 && (
              <Box className="agent-messages-container">
                <Typography className="agent-messages-title">Agent Messages:</Typography>
                {message.current_children.map((agentMessage, index) => (
                  <AgentMessage
                    key={agentMessage.current_id}
                    message={agentMessage}
                    onUpdateMessageInput={onUpdateMessageInput}
                    onRunMessage={onRunMessage}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    selectedCellId={selectedCellId}
                    onCellSelect={onCellSelect}
                    onToggleVersion={onToggleVersion}
                    registerMessageRef={registerMessageRef}
                    registerToggleOperation={registerToggleOperation} // Pass the prop to AgentMessage
                  />
                ))}
              </Box>
            )}

            {message.additional_metadata && (
              <Box>
                <Box
                  className="metadata-toggle"
                  onClick={handleToggleMetadata}
                >
                  <Typography className="metadata-label">
                    Metadata
                    <IconButton size="small" sx={{ ml: 1, p: 0.5 }}>
                      {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                    </IconButton>
                  </Typography>
                </Box>

                <Collapse in={metadataExpanded}>
                  <Box className="metadata-content">
                    <Typography
                      component="pre"
                      className="metadata-text"
                    >
                      {JSON.stringify(message.additional_metadata, null, 2)}
                    </Typography>
                  </Box>
                </Collapse>
              </Box>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export default PhaseMessage;