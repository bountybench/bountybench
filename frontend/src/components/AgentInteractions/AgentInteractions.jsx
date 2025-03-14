import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, CircularProgress, Button } from '@mui/material';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import StopIcon from '@mui/icons-material/Stop';
import PhaseMessage from './components/PhaseMessage/PhaseMessage';
import './AgentInteractions.css';
import RestoreIcon from '@mui/icons-material/Restore';

const AgentInteractions = ({
  interactiveMode,
  workflowStatus,
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
  const topAnchorRef = useRef(null);

  // Store a map of message toggle operations (sourceId -> targetId)
  const messageVersionMap = useRef(new Map());

  // Flag to prevent automatic bottom scrolling when toggling
  const [isTogglingVersion, setIsTogglingVersion] = useState(false);

  // Simple pass-through function
  const registerMessageRef = useCallback(() => { }, []);

  // Register a toggle operation before it happens
  const registerToggleOperation = useCallback((currentId, targetId, direction) => {
    console.log(`Registering toggle operation: ${currentId} -> ${targetId} (${direction})`);
    messageVersionMap.current.set(currentId, { targetId, direction });
  }, []);

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && event.altKey) {
      event.preventDefault();
      onTriggerNextIteration();
    }
  }, [onTriggerNextIteration]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isEditing, handleKeyDown, onTriggerNextIteration]);

  // Track the last ID we tried to scroll to
  const lastAttemptedScrollId = useRef(null);

  // Set up isTogglingVersion flag
  useEffect(() => {
    if (lastToggledMessageId) {
      console.log("Setting isTogglingVersion to true");
      setIsTogglingVersion(true);

      // Clear the flag after a longer time to prevent any race conditions
      const clearFlagTimeout = setTimeout(() => {
        console.log("Clearing isTogglingVersion flag");
        setIsTogglingVersion(false);
      }, 2000);

      return () => clearTimeout(clearFlagTimeout);
    }
  }, [lastToggledMessageId]);

  // Improved scroll effect with direct scrolling (no two-step process)
  useEffect(() => {
    if (!lastToggledMessageId || lastToggledMessageId === lastAttemptedScrollId.current) {
      return;
    }

    lastAttemptedScrollId.current = lastToggledMessageId;
    console.log("Toggle detected for message ID:", lastToggledMessageId);

    // Get the TARGET ID from our map
    const toggleInfo = messageVersionMap.current.get(lastToggledMessageId);
    if (!toggleInfo) {
      console.error("No toggle info found for message:", lastToggledMessageId);
      console.log("Make sure you've updated both PhaseMessage.jsx and AgentMessage.jsx!");
      return;
    }

    const targetId = toggleInfo.targetId;
    console.log(`Looking for target message with ID: ${targetId}`);

    // Wait for React to finish rendering, then scroll directly to target
    const findAndScrollToTarget = () => {
      // Look for the correct target element
      let targetElement = document.querySelector(`#message-${targetId}`);
      if (!targetElement) {
        targetElement = document.querySelector(`[data-message-id="${targetId}"]`);
      }

      if (targetElement) {
        console.log("✅ Found target message, scrolling to it:", targetId);

        // Get the container's scroll position and the element's position
        const containerRect = containerRef.current.getBoundingClientRect();
        const elementRect = targetElement.getBoundingClientRect();

        // Calculate desired scroll position (element at top with padding)
        const padding = 30; // pixels of padding at the top
        const desiredScrollTop = containerRef.current.scrollTop +
          (elementRect.top - containerRect.top) -
          padding;

        // Perform a smooth scroll directly to the target position
        containerRef.current.scrollTo({
          top: desiredScrollTop,
          behavior: 'smooth'
        });

        console.log("Applied smooth scrolling to target with padding");
      } else {
        console.error(`❌ Target message element not found: ${targetId}`);
        console.log("Dumping all current message element IDs for debugging:");
        const allMessageElements = document.querySelectorAll('.agent-message-container');
        Array.from(allMessageElements).forEach(el => {
          console.log(`- Element ID: ${el.id}, data-message-id: ${el.getAttribute('data-message-id')}`);
        });
      }

      // Clean up the map entry
      messageVersionMap.current.delete(lastToggledMessageId);
    };

    // First attempt after a delay
    const firstAttemptTimeout = setTimeout(findAndScrollToTarget, 300);

    // If the first attempt fails, try again with a longer delay
    const secondAttemptTimeout = setTimeout(() => {
      const targetElement = document.querySelector(`#message-${targetId}`) ||
        document.querySelector(`[data-message-id="${targetId}"]`);

      if (!targetElement) {
        console.log("First attempt failed, trying again...");
        findAndScrollToTarget();
      }
    }, 800);

    return () => {
      clearTimeout(firstAttemptTimeout);
      clearTimeout(secondAttemptTimeout);
    };
  }, [lastToggledMessageId]);

  // Only scroll to bottom when not toggling and messages update
  useEffect(() => {
    if (!isTogglingVersion && !lastToggledMessageId && messagesEndRef.current) {
      console.log("No toggle in progress, scrolling to bottom");
      const timeoutId = setTimeout(() => {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      return () => clearTimeout(timeoutId);
    } else {
      console.log("Skipping auto-scroll to bottom because toggle is in progress");
    }
  }, [phaseMessages, lastToggledMessageId, isTogglingVersion]);

  useEffect(() => {
    console.log('Phase Messages updated:', phaseMessages);
  }, [phaseMessages]);

  const handleStopClick = async () => {
    setIsStopping(true);
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
      <Box className="messages-container" ref={containerRef}>
        {/* Top anchor for scrolling to top first - kept for compatibility but not used */}
        <div ref={topAnchorRef} style={{ height: 0, overflow: 'hidden' }} id="top-scroll-anchor"></div>

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