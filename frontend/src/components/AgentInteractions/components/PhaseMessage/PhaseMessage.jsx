import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateMessageInput, onRerunMessage, onEditingChange, isEditing }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  const [agentsVersionChain, setAgentsVersionChain] = useState([]);

  useEffect(() => {
    if (message.current_children){
      const children = message.current_children;
      if (children.length === 0) return;
  
      setAgentsVersionChain(currentChain => {
        const chainCopy = [...currentChain];
        const numAgents = chainCopy.length;
        
        children.forEach((currChild, i) => {
          const agentId = currChild.agent_id;
          if (i >= numAgents) {
            chainCopy.push({ agent: agentId, versionChain: [currChild], index: 1 });
          } else {
            const existingVersions = chainCopy[i].versionChain;
            const foundIndex = existingVersions.findIndex(v => v.current_id === currChild.current_id);
            if (foundIndex !== -1) {
              existingVersions[foundIndex] = currChild;
            } else {
              existingVersions.push(currChild);
              chainCopy[i].index = existingVersions.length;
            }
          }
        });
  
        return chainCopy;
      });
    }
  }, [message.current_children]);

  const handleChildUpdate = (id, num) => {
    if (id !== 'executor_agent'){
      const chain_copy = [...agentsVersionChain]; 
      const agent_index = chain_copy.findIndex(item => item.agent === id);
      chain_copy[agent_index]['index'] += num;
      // If followed by executor agent, also change the displayed index of the executor's output
      if (agent_index + 1 < chain_copy.length){
        chain_copy[agent_index+1]['index'] += num;
      }
      setAgentsVersionChain(chain_copy);
    }
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
            
            {agentsVersionChain && agentsVersionChain.length > 0 && (
              <Box className="agent-messages-container">
                <Typography className="agent-messages-title">Agent Messages:</Typography>
                {agentsVersionChain.map((messages, index) => (
                  <AgentMessage 
                    key={index} 
                    message={messages['versionChain'][messages['index'] - 1]} 
                    onUpdateMessageInput={onUpdateMessageInput}
                    onRerunMessage={onRerunMessage}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    onPhaseChildUpdate={handleChildUpdate}
                    phaseDisplayedIndex={messages['index']}
                    phaseVersionLength={messages['versionChain'].length}
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