import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateActionInput, onEditingChange, isEditing, selectedCellId, onCellSelect, cellRefs }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

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
            
            {message.current_children && message.current_children.length > 0 && (
              <Box className="agent-messages-container">
                <Typography className="agent-messages-title">Agent Messages:</Typography>
                {message.current_children.map((agentMessage, index) => (
                  <div ref={(el) => (cellRefs.current[agentMessage.current_id] = el)} key={agentMessage.current_id}>                  
                    <AgentMessage 
                      key={agentMessage.current_id}
                      message={agentMessage} 
                      onUpdateActionInput={onUpdateActionInput}
                      onEditingChange={onEditingChange}
                      isEditing={isEditing}
                      selectedCellId={selectedCellId}
                      onCellSelect={onCellSelect}
                      cellRefs={cellRefs}
                    />
                  </div>
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