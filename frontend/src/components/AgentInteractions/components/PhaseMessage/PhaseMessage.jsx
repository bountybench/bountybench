import React, { useState, useCallback } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from '../AgentMessage/AgentMessage';
import './PhaseMessage.css'

const PhaseMessage = ({ message, onUpdateMessageInput, onRunMessage, onEditingChange, isEditing, selectedCellId, onCellSelect, onToggleVersion }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);
  const [commandsExpanded, setCommandsExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);
  const handleToggleCommands = () => setCommandsExpanded(!commandsExpanded);

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

  const processLMCalls = () => {
    let totalCalls = 0;
    let commands = [];
    
    if (!message.current_children || message.current_children.length === 0) {
      return { totalCalls, commands };
    }
    
    message.current_children.forEach(agentMessage => {
      if (agentMessage.action_messages && Array.isArray(agentMessage.action_messages)) {
        const modelActions = agentMessage.action_messages.filter(
          action => action.resource_id === "model"
        );
        
        totalCalls += modelActions.length;
        
        modelActions.forEach(action => {
          if (action.command) {
            commands.push(action.command);
          }
        });
      }
    });
    
    return { totalCalls, commands };
  };

  const { totalCalls: lmCalls, commands } = processLMCalls();

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
              <>
                <Typography className="phase-summary" sx={{ marginTop: 1 }}>
                  LM Calls: {lmCalls || '(no LM calls)'}
                </Typography>
                
                {commands.length > 0 && (
                  <Box className="command-summary-container" sx={{ width: '100%' }}>
                    <Box 
                      className="command-summary-header" 
                      onClick={handleToggleCommands}
                      sx={{ 
                        alignItems: 'center', 
                        cursor: 'pointer',
                        marginTop: 1,
                      }}
                    >
                      <Typography className="phase-summary" sx={{width: '100%'}}>
                        Command Log
                        <IconButton 
                          size="smaller" 
                          className="command-toggle-button"
                          aria-label="toggle commands"
                          sx={{ color: 'black', ml: 5 }}
                        >
                          {commandsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </Typography>
                    </Box>
                    
                    <Collapse in={commandsExpanded}>
                      <Box 
                        className="commands-list"
                        sx={{ 
                          backgroundColor: '#f5f5f5',
                          padding: 1.5,
                          borderRadius: 1,
                          marginBottom: 1.5
                        }}
                      >
                        {commands.map((command, index) => (
                          <Typography 
                            key={index} 
                            className="command-item"
                            sx={{ 
                              fontSize: '0.8rem',
                              marginBottom: index < commands.length - 1 ? 1 : 0
                            }}
                          >
                            {index + 1}. {command}
                          </Typography>
                        ))}
                      </Box>
                    </Collapse>
                  </Box>
                )}
              </>
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