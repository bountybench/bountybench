import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateActionInput, onRerunAction, onEditingChange, isEditing }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  const [phaseDisplayedIndex, setPhaseDisplayedIndex] = useState(1);
  const [phaseMultiVersion, setPhaseMultiVersion] = useState(false);

  useEffect(() => {
    if (message.agent_messages){
      const messageLength = message.agent_messages.length;
      // Make sure that both system and agent are received
      if (messageLength % 2 !== 0 || messageLength <= 2) {
        return;
      }
      setPhaseMultiVersion(true);
      setPhaseDisplayedIndex(messageLength / 2);
      
    }
  }, [message, message.agent_messages]);

  const handleChildUpdate = (num) => {
    setPhaseDisplayedIndex((prev) => prev + num);
  };

  return (
    <Box className="message-container phase">
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
            
            {message.agent_messages && message.agent_messages.length > 0 && (
              <Box className="agent-messages-container">
                <Typography className="agent-messages-title">Agent Messages:</Typography>
                {message.agent_messages.slice(2*phaseDisplayedIndex-2, 2*phaseDisplayedIndex).map((agentMessage, index) => (
                  <AgentMessage 
                    key={index} 
                    message={agentMessage} 
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    onPhaseChildUpdate={handleChildUpdate}
                    phaseMultiVersion={phaseMultiVersion}
                    phaseDisplayedIndex={phaseDisplayedIndex}
                    phaseVersionLength={message.agent_messages.length / 2}
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