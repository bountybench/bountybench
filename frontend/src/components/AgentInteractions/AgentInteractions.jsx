import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';
import RestoreIcon from '@mui/icons-material/Restore';

const AgentInteractions = ({
  interactiveMode,
  workflowStatus, // Pass workflowStatus from parent
  isNextDisabled,
  phaseMessages = [],
  onUpdateMessageInput,
  onRunMessage,
  onTriggerNextIteration,
  onStopWorkflow,
  onToggleVersion,
  onRestart
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [stopped, setStopped] = useState(false);
  const messagesEndRef = useRef(null);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const prevMessagesLengthRef = useRef(0);

  // Store message structure for comparison
  const prevMessageStructureRef = useRef("");

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && event.altKey) {
      event.preventDefault(); // Prevent the default action
      onTriggerNextIteration();
    }
  }, [onTriggerNextIteration]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isEditing, handleKeyDown, onTriggerNextIteration]);

  useEffect(() => {
    if (phaseMessages.length === 0) return;

    // Create a simplified representation of the message structure 
    // that ignores content changes but captures structural changes
    const getMessageStructure = (messages) => {
      return messages.map(msg => ({
        id: msg.current_id,
        children: msg.current_children ? getMessageStructure(msg.current_children) : []
      }));
    };

    const currentStructure = JSON.stringify(getMessageStructure(phaseMessages));
    const prevStructure = prevMessageStructureRef.current;

    // Detect if new messages were added or if this is just a content update
    const isNewMessage = phaseMessages.length > prevMessagesLengthRef.current;
    const isStructuralChange = currentStructure !== prevStructure && prevStructure !== "";

    // Only scroll if new messages were added (ignoring content updates)
    if (isNewMessage || (isStructuralChange && !selectedCellId)) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }

    // Update refs for next comparison
    prevMessagesLengthRef.current = phaseMessages.length;
    prevMessageStructureRef.current = currentStructure;
  }, [phaseMessages, selectedCellId]);

  // Custom handler for toggling versions
  const handleToggleVersion = useCallback((messageId, direction) => {
    // Just call the original without any auto-scrolling
    onToggleVersion(messageId, direction);
  }, [onToggleVersion]);

  useEffect(() => {
    console.log('Phase Messages updated:', phaseMessages);
  }, [phaseMessages]);

  const handleStopClick = async () => {
    setIsStopping(true); // Hide buttons immediately
    await onStopWorkflow();
    setStopped(true);
  };

  const handleRestart = async () => {
    await onRestart();
  };

  useEffect(() => {
    if (workflowStatus === "stopped") {
      setIsStopping(true);
      setStopped(true);
    }
    else {
      setIsStopping(false);
      setStopped(false);
    }
  }, [workflowStatus]);

  if (phaseMessages.length === 0) {
    return (
      <Box className="interactions-container" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="interactions-container">
      <Box className="messages-container">
        {phaseMessages.map((phaseMessage, index) => (
          <PhaseMessage
            key={phaseMessage.current_id}
            message={phaseMessage}
            onUpdateMessageInput={onUpdateMessageInput}
            onRunMessage={onRunMessage}
            onEditingChange={setIsEditing}
            isEditing={isEditing}
            selectedCellId={selectedCellId}
            onCellSelect={setSelectedCellId}
            onToggleVersion={handleToggleVersion}
          />
        ))}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex" justifyContent="center" gap={1}>
        {interactiveMode && (
          <>
            {!isStopping && !stopped ? (
              <>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={onTriggerNextIteration}
                  startIcon={<KeyboardDoubleArrowRightIcon />}
                  disabled={isNextDisabled}
                  size="small"
                >
                  Continue
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={handleStopClick}
                  startIcon={<StopIcon />}
                  size="small"
                >
                  Stop
                </Button>
              </>
            ) : null}
            {isStopping && stopped && (
              <Button
                variant="contained"
                color="primary"
                onClick={handleRestart}
                startIcon={<RestoreIcon />}
                size="small"
              >
                Resume
              </Button>
            )}
          </>
        )}
      </Box>
    </Box>
  );
};

export default AgentInteractions;