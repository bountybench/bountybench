import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateActionInput, onRerunAction, onEditingChange, isEditing, selectedCellId, onCellSelect, cellRefs }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  const [agentsVersionChain, setAgentsVersionChain] = useState([]);
  const cellIds = useRef([]); // store cell IDs

  const getAgentIds = (agents) => agents.length === 0 ? [] : agents.map(agent => agent.current_id);

  // Collect cell IDs whenever agents version chain is updated
  useEffect(() => {
    cellIds.current = agentsVersionChain.map(messages => messages['versionChain'][messages['index'] - 1].current_id);
  }, [agentsVersionChain]);

  // Navigation functions
  const getNextId = (currentId) => {
    if (!currentId) return cellIds.current[0];
    const index = cellIds.current.indexOf(currentId);
    return cellIds.current[Math.min(index + 1, cellIds.current.length - 1)];
  };

  const getPrevId = (currentId) => {
    if (!currentId) return cellIds.current[0];
    const index = cellIds.current.indexOf(currentId);
    return cellIds.current[Math.max(index - 1, 0)];
  };

  const scrollToCell = (cellId) => {
    const cellElement = cellRefs.current[cellId];
    if (cellElement) {
      cellElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  // Keydown listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        onCellSelect(prev => {
          const newId = getNextId(prev);
          scrollToCell(newId); // Scroll to new cell
          return newId;
        });
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        onCellSelect(prev => {
          const newId = getPrevId(prev);
          scrollToCell(newId); // Scroll to new cell
          return newId;
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [onCellSelect]);

  useEffect(() => {
    if (message.current_children){
      const children_length = message.current_children.length;
      if (children_length === 0){
        return;
      }
      const chain_copy = [...agentsVersionChain]; 
      const num_agents = agentsVersionChain.length;
      for (let i = 0; i < children_length; i++) {
        const curr_child = message.current_children[i];
        const agent_id = curr_child.agent_id;
        if (i >= num_agents){
          chain_copy.push({'agent': agent_id, 'versionChain': [curr_child], 'index': 1});
        }
        else{
          const found_index = getAgentIds(chain_copy[i]['versionChain']).indexOf(curr_child.current_id);
          if (found_index !== -1){
            chain_copy[i]['versionChain'][found_index] = curr_child
          }
          else{
            chain_copy[i]['versionChain'].push(curr_child);
            chain_copy[i]['index'] = chain_copy[i]['versionChain'].length;
          }
        }
        }
        setAgentsVersionChain(chain_copy);      
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
                  <div ref={(el) => (cellRefs.current[messages['versionChain'][messages['index'] - 1].current_id] = el)} key={messages['versionChain'][messages['index'] - 1].current_id}>
                    <AgentMessage 
                      key={index} 
                      message={messages['versionChain'][messages['index'] - 1]} 
                      onUpdateActionInput={onUpdateActionInput}
                      onRerunAction={onRerunAction}
                      onEditingChange={onEditingChange}
                      isEditing={isEditing}                      
                      selectedCellId={selectedCellId}
                      onCellSelect={onCellSelect}
                      cellRefs={cellRefs}
                      onPhaseChildUpdate={handleChildUpdate}
                      phaseDisplayedIndex={messages['index']}
                      phaseVersionLength={messages['versionChain'].length}
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