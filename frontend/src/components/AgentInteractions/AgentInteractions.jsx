import React, { useRef, useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';

const AgentInteractions = ({ 
  interactiveMode, 
  isNextDisabled,
  messages = [],
  onUpdateActionInput,
  onTriggerNextIteration,
}) => {
  const messagesEndRef = useRef(null);
  const cellRefs = useRef({}); 

  const [isEditing, setIsEditing] = useState(false);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const [cellIds, setCellIds] = useState([]);

  // Find the latest PhaseMessage
  const latestPhaseMessage = messages.filter(msg => msg.message_type === 'PhaseMessage').pop();
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Generate ordered list of cell IDs
  useEffect(() => {
    if (latestPhaseMessage) {
      const ids = [];
      // Add Agent Messages and their Actions
      latestPhaseMessage.current_children?.forEach(agentMsg => {
        if (agentMsg.current_id && agentMsg.current_children?.length == 0) ids.push(agentMsg.current_id);
        agentMsg.current_children?.forEach(actionMsg => {
          if (actionMsg.current_id) ids.push(actionMsg.current_id);
        });
      });

      setCellIds(ids);
      if (ids.length > 0 && !selectedCellId) setSelectedCellId(ids[0]);
    } else {
      setCellIds([]);
      setSelectedCellId(null);
    }
  }, [latestPhaseMessage]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = e.key.toLowerCase();

      if (isEditing) {
        if (key === 'escape') {
          e.preventDefault();
          setIsEditing(false); // Exit edit mode on Escape
        }
        return; // Prevent navigation while editing
      }

      if (key === 'enter') {
        e.preventDefault();
        // Check for Shift or Ctrl/Cmd modifiers
        if (e.shiftKey || (e.ctrlKey || e.metaKey)) {
          // Trigger rerun action for current cell
          console.log("Triggering next iteration");
          onTriggerNextIteration(selectedCellId); 
          return; // Prevent other default behavior
        }
        setIsEditing(true); // Enter edit mode on normal Enter
        return;
      }

      // Navigation
      if (key === 'arrowdown' || key === 'j') {
        e.preventDefault();
        setSelectedCellId(prev => {
          const newId = getNextId(prev);
          scrollToCell(newId); // Scroll to new cell
          return newId;
        });
      } else if (key === 'arrowup' || key === 'k') {
        e.preventDefault();
        setSelectedCellId(prev => {
          const newId = getPrevId(prev);
          scrollToCell(newId); // Scroll to new cell
          return newId;
        });
      }
    };

    const getNextId = (currentId) => {
      if (!currentId) return cellIds[0];
      const index = cellIds.indexOf(currentId);
      return cellIds[Math.min(index + 1, cellIds.length - 1)];
    };

    const getPrevId = (currentId) => {
      if (!currentId) return cellIds[0];
      const index = cellIds.indexOf(currentId);
      return cellIds[Math.max(index - 1, 0)];
    };

    const scrollToCell = (cellId) => {
      const cellElement = cellRefs.current[cellId];
      if (cellElement) {
        cellElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [cellIds, isEditing]);

  if (!messages || messages.length === 0) {  // Handle empty messages here
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="interactions-container">
      <Box className="messages-container">
        {!latestPhaseMessage ? (
          <Typography variant="body2" color="text.secondary" align="center">
            No Phase messages yet
          </Typography>
        ) : (
          <PhaseMessage
            message={latestPhaseMessage}
            onUpdateActionInput={onUpdateActionInput}
            onEditingChange={setIsEditing}
            isEditing={isEditing}
            selectedCellId={selectedCellId}
            onCellSelect={setSelectedCellId}
            cellRefs={cellRefs}
          />
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex">
        <Box className="buttons-wrapper" display="flex" flexDirection="column" justifyContent="flex-end">
          {interactiveMode && (
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={onTriggerNextIteration}
                startIcon={<ArrowForwardIcon />}
                disabled={isNextDisabled || isEditing}
                size="small"
                sx={{ mb: 1 }}
              >
                Next
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default AgentInteractions;