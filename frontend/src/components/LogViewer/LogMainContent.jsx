import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import PhaseMessage from '../AgentInteractions/components/PhaseMessage/PhaseMessage.jsx';

const LogMainContent = ({ 
  selectedLogFile, 
  loading, 
  selectedLogContent, 
  isEditing, 
  setIsEditing, 
  selectedCellId, 
  setSelectedCellId, 
  handleRerunMessage, 
  handleUpdateMessageInput 
}) => {
  return (
    <Box className="log-main-container">
      <Typography variant="subtitle1" gutterBottom>
        {selectedLogFile ? `Viewing ${selectedLogFile}` : 'Pick a log file to view.'}
      </Typography>
      {loading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      )}
      {!loading && selectedLogContent && (
        <Box className="log-item-container">
          {selectedLogContent.map((phase, index) => (
            <PhaseMessage
              key={index}
              message={{
                phase_name: phase.phase_id,
                phase_summary: phase.phase_summary,
                phase_usage: phase.phase_usage || {},
                current_children: phase.agent_messages || [],
                additional_metadata: phase.additional_metadata || null,
              }}
              onEditingChange={setIsEditing}            
              isEditing={isEditing}            
              selectedCellId={selectedCellId}
              onCellSelect={setSelectedCellId}
              onRerunMessage={handleRerunMessage}
              onUpdateMessageInput={handleUpdateMessageInput}
            />
          ))}
        </Box>
      )}
    </Box>
  );
};

export default LogMainContent;