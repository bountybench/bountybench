import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AgentMessage from './AgentMessage';

const PhaseMessage = ({ message, onUpdateActionInput, onRerunAction }) => {
  const [contentExpanded, setContentExpanded] = useState(true);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  const handleToggleContent = () => setContentExpanded(!contentExpanded);
  const handleToggleMetadata = () => setMetadataExpanded(!metadataExpanded);

  return (
    <Box className="message-container phase">
      <Card className="message-bubble phase-bubble">
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle2" color="text.secondary">
              Phase: {message.phase_name}
            </Typography>
            <IconButton size="small" onClick={handleToggleContent}>
              {contentExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={contentExpanded}>
            <Typography variant="body2" mt={1}>
              Summary: {message.phase_summary || '(no summary)'}
            </Typography>
            
            {message.current_children && message.current_children.length > 0 && (
              <Box mt={2}>
                <Typography variant="subtitle2">Agent Messages:</Typography>
                {message.current_children.map((agentMessage, index) => (
                  <AgentMessage 
                    key={index} 
                    message={agentMessage} 
                    onUpdateActionInput={onUpdateActionInput}
                    onRerunAction={onRerunAction}
                  />
                ))}
              </Box>
            )}

            {message.additional_metadata && (
              <Box mt={2}>
                <Box 
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    cursor: 'pointer',
                    py: 0.5,
                    '&:hover': {
                      bgcolor: 'rgba(0, 0, 0, 0.04)',
                    },
                  }}
                  onClick={handleToggleMetadata}
                >
                  <Typography 
                    variant="caption" 
                    color="text.secondary" 
                    sx={{ 
                      display: 'flex', 
                      alignItems: 'center',
                      fontWeight: 'medium'
                    }}
                  >
                    Metadata
                    <IconButton size="small" sx={{ ml: 1, p: 0.5 }}>
                      {metadataExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                    </IconButton>
                  </Typography>
                </Box>
                
                <Collapse in={metadataExpanded}>
                  <Box mt={1}>
                    <Card variant="outlined" sx={{ bgcolor: '#f5f5f5', p: 1 }}>
                      <Typography
                        variant="body2"
                        component="pre"
                        sx={{
                          whiteSpace: 'pre-wrap',
                          overflowX: 'auto',
                          m: 0,
                          fontFamily: 'monospace',
                          fontSize: '0.85rem'
                        }}
                      >
                        {JSON.stringify(message.additional_metadata, null, 2)}
                      </Typography>
                    </Card>
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