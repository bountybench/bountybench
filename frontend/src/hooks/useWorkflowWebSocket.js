import { useState, useEffect, useCallback, useRef } from 'react';

import { WS_BASE_URL } from '../config'; 

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [phaseMessages, setPhaseMessages] = useState([]);
  const [error, setError] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const lastHeartbeat = useRef(Date.now());
  const heartbeatInterval = useRef(null);
  const connectionTimeout = useRef(null);
  const connectionEstablished = useRef(false);

  const handleUpdatePhaseMessage = useCallback((updatedPhaseMessage) => {
    setCurrentPhase(updatedPhaseMessage);
    setPhaseMessages(prevPhaseMessages => {
      const updatedMessages = Array.isArray(updatedPhaseMessage) ? updatedPhaseMessage : [updatedPhaseMessage];
      
      let updated = false;
      const newPhaseMessages = prevPhaseMessages.reduce((acc, phase) => {
        if (!updated && updatedMessages.some(um => um.current_id === phase.current_id)) {
          // Found the phase to update
          acc.push(...updatedMessages.filter(um => !acc.some(p => p.current_id === um.current_id)));
          updated = true;
        } else if (!updated) {
          // Keep phases before the update
          acc.push(phase);
        }
        // Phases after the update are dropped
        return acc;
      }, []);

      // If no existing phase was updated, append the new phase(s)
      if (!updated) {
        newPhaseMessages.push(...updatedMessages);
      }

      return newPhaseMessages;
    });
  }, [])

  const handleUpdatedAgentMessage = useCallback((updatedAgentMessage) => {
    const updatedMessages = Array.isArray(updatedAgentMessage) ? updatedAgentMessage : [updatedAgentMessage];
    if (!updatedMessages[0].parent) {
      console.error("Agent should already have parent set");
      return;
    }

    setPhaseMessages(prevPhaseMessages => {
      return prevPhaseMessages.map(phase => {
        if (phase.current_id === updatedMessages[0].parent) {
          let updatedAgentMessages = [...(phase.current_children || [])];
          
          const newMessage = updatedMessages[0];
          if (newMessage.prev) {
            const prevIndex = updatedAgentMessages.findIndex(am => am.current_id === newMessage.prev);
            if (prevIndex !== -1) {
              // Keep messages up to and including the prev message, then append the new message
              updatedAgentMessages = [...updatedAgentMessages.slice(0, prevIndex + 1), newMessage];
            } else {
              // If prev not found, log for now, this isn't a reasonable scenario
              console.log(`No prev found for ${newMessage}`);
            }
          } else {
            // If no prev, replace all messages with the new message
            updatedAgentMessages = [newMessage];
          }
          
          return {
            ...phase,
            current_children: updatedAgentMessages
          };
        }
        return phase;
      });
    });
  }, []);

  const handleUpdatedActionMessage = useCallback((updatedActionMessage) => {
    const updatedMessages = Array.isArray(updatedActionMessage) ? updatedActionMessage : [updatedActionMessage];
    if (!updatedMessages[0].parent) {
      console.error("Action message should already have parent set");
      return;
    }
  
    setPhaseMessages(prevPhaseMessages => {
      return prevPhaseMessages.map(phase => {
        return {
          ...phase,
          current_children: (phase.current_children || []).map(agentMessage => {
            if (agentMessage.current_id === updatedMessages[0].parent) {
              let updatedActionMessages = [...(agentMessage.current_children || [])];
              
              const newMessage = updatedMessages[0];
              if (newMessage.prev) {
                const prevIndex = updatedActionMessages.findIndex(am => am.current_id === newMessage.prev);
                if (prevIndex !== -1) {
                  // Keep messages up to and including the prev message, then append the new message
                  updatedActionMessages = [...updatedActionMessages.slice(0, prevIndex + 1), newMessage];
                } else {
                  // If prev not found, log for now, this isn't a reasonable scenario
                  console.log(`No prev found for ${newMessage}`);
                }
              } else {
                // If no prev, replace all messages with the new message
                updatedActionMessages = [newMessage];
              }
              
              return {
                ...agentMessage,
                current_children: updatedActionMessages
              };
            }
            return agentMessage;
          })
        };
      });
    });
  }, []);

  const handleWebSocketMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.data);
      
      // Handle heartbeat
      if (data.type === 'ping') {
        lastHeartbeat.current = Date.now();
        ws.current?.send(JSON.stringify({ type: 'pong' }));
        return;
      }

      // Handle single message or list of messages
      const messages = Array.isArray(data) ? data : [data];

      messages.forEach(message => {
        if (message.error) {
          console.error(`${message.message_type}: ${message.error} ${message.traceback}`);
          setError(message.error);
        }
        
        switch (message.message_type) {
          case 'connection_established':
            connectionEstablished.current = true;
            setIsConnected(true);
            break;

          case 'workflow_status':
            console.log(`Received workflow status update: ${message.status}`);
            setWorkflowStatus(message.status);
            break;

          case 'WorkflowMessage':
            if (message.workflow_metadata?.workflow_summary) {
              console.log(`Received workflow message summary update: ${message.status}`);
              setWorkflowStatus(message.workflow_metadata.workflow_summary);
            }
            break;

          case 'PhaseMessage':
            handleUpdatePhaseMessage(message);
            break;

          case 'AgentMessage':
            handleUpdatedAgentMessage(message);
            break;

          case 'ActionMessage':
            handleUpdatedActionMessage(message);
            break;

          case 'workflow_completed':
            console.log(`Received workflow status update (should be complete): ${message.status}`);
            setWorkflowStatus('completed');
            break;

          default:
            console.error('Unknown message_type:', message.message_type);
        }
      });
    } catch (err) {
      console.error('Error processing WebSocket message:', err);
      setError('Failed to process workflow update: ' + err.message);
    }
  }, [handleUpdatePhaseMessage, handleUpdatedAgentMessage, handleUpdatedActionMessage]);

  const cleanupConnection = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }
    if (connectionTimeout.current) {
      clearTimeout(connectionTimeout.current);
      connectionTimeout.current = null;
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    connectionEstablished.current = false;
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) return;

    const backoff = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
    connectionTimeout.current = setTimeout(() => {
      const wsUrl = `${WS_BASE_URL}/ws/${workflowId}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        clearTimeout(connectionTimeout.current);
        reconnectAttempts.current = 0;
        lastHeartbeat.current = Date.now();
      };

      ws.current.onclose = (event) => {
        if (!event.wasClean) {
          reconnectAttempts.current += 1;
          connect();
        }
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Handle heartbeat first
        if (data.message_type === "ping") {
          ws.current.send(JSON.stringify({ message_type: "pong" }));
          lastHeartbeat.current = Date.now();
          return;
        }

        // Process application messages
        handleWebSocketMessage(event);
        
        // Update last heartbeat on any valid message
        lastHeartbeat.current = Date.now();
      };
    }, backoff);
  }, [workflowId, maxReconnectAttempts, handleWebSocketMessage]);

  useEffect(() => {
    if (workflowId) {
      connect();
      return () => {
        cleanupConnection();
      };
    }
  }, [connect, workflowId, cleanupConnection]);

  return {
    isConnected,
    phaseMessages,
    error,
    workflowStatus,
    currentPhase,
  };
};