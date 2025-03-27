import React, { useState, useCallback } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateMessageInput, onRunMessage, onEditingChange, isEditing, selectedCellId, onCellSelect, onToggleVersion }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  const iterationCount = useCallback(() => {
    if (!message?.current_children || !Array.isArray(message.current_children)) {
      return 0;
    }
    
    let iterations = message.current_children.length;
    
    if (iterations > 0 && message.current_children[0].agent_id === 'system') {
      iterations = iterations - 1;
    }
    
    return iterations;
  }, [message?.current_children]);

  const iterations = iterationCount();
  
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
            
            {iterations && (
              <Typography className="phase-summary">
                Iterations: {iterations || '(no iterations)'}
              </Typography>
            )}

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
                    iteration={index}
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