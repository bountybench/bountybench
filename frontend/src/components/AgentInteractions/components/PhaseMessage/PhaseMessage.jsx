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
  const [versionChain, setVersionChain] = useState([message.current_children]);

  const getAgentIds = (agents) => agents.length === 0 ? [] : agents.map(agent => agent.current_id);
  const arraysEqual = (arr1, arr2) => JSON.stringify(arr1) === JSON.stringify(arr2);

  useEffect(() => {
    if (message.agent_messages){
      const curr_children = message.current_children;
      const versionLength = versionChain.length;
      const curr_children_ids = getAgentIds(curr_children);
      const all_agent_ids = getAgentIds(message.agent_messages);
      if (arraysEqual(all_agent_ids,curr_children_ids)){
        setVersionChain([curr_children]);
        return;
      }
      // when current children is not equal to latest version
      const last_version_ids = getAgentIds(versionChain[versionLength-1]);
      if (!arraysEqual(last_version_ids,curr_children_ids)) {
        // if all of current children is new, we have a new version
        if (curr_children_ids.filter(child => last_version_ids.includes(child)).length === 0){
          setVersionChain((prev) => {
            const newVersionChain = [...prev, curr_children];
            setPhaseDisplayedIndex(newVersionChain.length); // Uses the updated versionChain
            return newVersionChain;
          });
        }
        else{
          const newChildren = curr_children.filter(child => !last_version_ids.includes(child.current_id));
          setVersionChain(prev => prev.map((innerList, index) => 
              index === phaseDisplayedIndex - 1 ? [...innerList, ...newChildren] : innerList
            ));
        }
      }
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
            
            {message.agent_messages && message.current_children.length > 0 && (
              <Box className="agent-messages-container">
                <Typography className="agent-messages-title">Agent Messages:</Typography>
                {versionChain[phaseDisplayedIndex - 1].map((agentMessage, index) => (
                  <AgentMessage 
                    key={index} 
                    index={index}
                    message={agentMessage} 
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                    onEditingChange={onEditingChange}
                    isEditing={isEditing}
                    onPhaseChildUpdate={handleChildUpdate}
                    phaseDisplayedIndex={phaseDisplayedIndex}
                    phaseVersionLength={versionChain.length}
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