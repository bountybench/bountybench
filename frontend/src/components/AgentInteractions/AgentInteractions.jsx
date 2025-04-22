import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, CircularProgress, Button, TextField, FormControl, Select, MenuItem, InputLabel } from '@mui/material';
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
  onRestart,
  lastToggledMessageId
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [stopped, setStopped] = useState(false);
  const messagesEndRef = useRef(null);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const containerRef = useRef(null);
  const messageVersionMap = useRef(new Map());
  const [isTogglingVersion, setIsTogglingVersion] = useState(false);
  const lastAttemptedScrollId = useRef(null);
  const [selectedIterNum, setSelectedIterNum] = useState(1);
  const [selectedIterType, setSelectedIterType] = useState('agent');
  const [responding, setResponding] = useState(false);
  const registerMessageRef = useCallback(() => { }, []);

  const registerToggleOperation = useCallback((currentId, targetId, direction) => {
    messageVersionMap.current.set(currentId, { targetId, direction });
  }, []);

  const handleInputChange = (event) => {
    const value = parseInt(event.target.value, 10);
    setSelectedIterNum(isNaN(value) || value < 0 ? 0 : value);
  };

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && event.altKey) {
      event.preventDefault(); // Prevent the default action
      onTriggerNextIteration(selectedIterNum, selectedIterType);
    }
  }, [selectedIterNum, selectedIterType, onTriggerNextIteration]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isEditing, handleKeyDown, onTriggerNextIteration]);

  useEffect(() => {
    if (lastToggledMessageId) {
      setIsTogglingVersion(true);

      const clearFlagTimeout = setTimeout(() => {
        setIsTogglingVersion(false);
      }, 2000);

      return () => clearTimeout(clearFlagTimeout);
    }
  }, [lastToggledMessageId]);

  useEffect(() => {
    if (!lastToggledMessageId || lastToggledMessageId === lastAttemptedScrollId.current) return;

    lastAttemptedScrollId.current = lastToggledMessageId;
    const toggleInfo = messageVersionMap.current.get(lastToggledMessageId);
    if (!toggleInfo) return;

    const targetId = toggleInfo.targetId;

    const scrollToTargetWhenAvailable = (retryCount = 0, maxRetries = 5) => {
      const targetElement = document.querySelector(`#message-${targetId}`) ||
        document.querySelector(`[data-message-id="${targetId}"]`);

      if (targetElement && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect();
        const elementRect = targetElement.getBoundingClientRect();
        const padding = 30;

        containerRef.current.scrollTo({
          top: containerRef.current.scrollTop + (elementRect.top - containerRect.top) - padding,
          behavior: 'smooth'
        });

        messageVersionMap.current.delete(lastToggledMessageId);
        return;
      }

      if (retryCount < maxRetries) {
        const delay = 200 * (retryCount + 1);
        const timeoutId = setTimeout(() => {
          scrollToTargetWhenAvailable(retryCount + 1, maxRetries);
        }, delay);

        return () => clearTimeout(timeoutId);
      } else {
        messageVersionMap.current.delete(lastToggledMessageId);
      }
    };

    return () => {
      scrollToTargetWhenAvailable();
    };
  }, [lastToggledMessageId]);

  // Only scroll to bottom when not toggling and messages update
  useEffect(() => {
    if (!isTogglingVersion && !lastToggledMessageId && messagesEndRef.current) {
      const timeoutId = setTimeout(() => {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      return () => clearTimeout(timeoutId);
    }
  }, [phaseMessages, lastToggledMessageId, isTogglingVersion]);

  useEffect(() => {
    console.log('Phase Messages updated:', phaseMessages);
    setResponding(false);
  }, [phaseMessages]);

  const handleStopClick = async () => {
    setIsStopping(true); // Hide buttons immediately    
    await onStopWorkflow();
    setStopped(true);
  };

  const handleContinueClick = () => {
    setResponding(true);  // Disable the button immediately
    onTriggerNextIteration(selectedIterNum, selectedIterType);  // Trigger the next iteration
  };

  const handleRestart = async () => {
    await onRestart();
  };

  // Ensure buttons remain hidden when workflow status updates from parent
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

  const isDisabled = isNextDisabled || responding;

  return (
    <Box className="interactions-container">
      <Box className="messages-container" ref={containerRef}>

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
            onToggleVersion={onToggleVersion}
            registerMessageRef={registerMessageRef}
            registerToggleOperation={registerToggleOperation}
          />
        ))}
        <div ref={messagesEndRef} />
      </Box>

      <Box className="input-and-buttons-container" display="flex" justifyContent="center" gap={1}>
        {interactiveMode && (
          <>
            {!isStopping && !stopped ? (
              <>
                <TextField
                  type="number"
                  label="Run X"
                  color="primary"
                  value={selectedIterNum}
                  onChange={handleInputChange}
                />
                <FormControl>
                  <InputLabel id="select-label">Iteration</InputLabel>
                  <Select
                    labelId="select-label"
                    label="Iteration"
                    value={selectedIterType}
                    onChange={(e) => setSelectedIterType(e.target.value)}
                  >
                    <MenuItem value="agent">Agent</MenuItem>
                    <MenuItem value="phase">Phase</MenuItem>
                  </Select>
                </FormControl>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleContinueClick}
                  startIcon={<KeyboardDoubleArrowRightIcon />}
                  disabled={isDisabled}
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
                Restart Resources
              </Button>
            )}
          </>
        )}
      </Box>
    </Box>
  );
};

export default AgentInteractions;