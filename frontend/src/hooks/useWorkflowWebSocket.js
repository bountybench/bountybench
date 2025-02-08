import { useState, useEffect, useCallback, useRef } from 'react';

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
    setCurrentPhase(message);
    // HERE WE NEED TO UPDATE PHASE MESSAGES
    // Essentially, if we are sending an update on an existing phase message (already in phaseMessages array),
    // we want to overwrite both the existing entry
    // AND clear all of the subsequent entries (e.g. we have [1, 2, 3, 4], update 2* > messages become [1, 2*])
    // The message may be an array of messages (all one type):
    // e.g. we have [1, 2, 3, 4], update [2*, 3*] > messages become [1, 2*, 3*]
    // Distinguish entries via "current_id"
  })

  const handleUpdatedAgentMessage = useCallback((updatedAgentMessage) => {
    
    // HERE WE NEED TO UPDATE AGENT MESSAGES
    // Agent messages are nested within a Phase message
    // the relevant phase message (id) can be retrieved via element.parent
    
    // We do not want to overwrite the existing phase message entry (note phase message is a dict)
    // instead, we want to update a property of the phase message (phase.agent_messages)
    // phase.agent_messages is a list of agent messages

    // Essentially, if we are sending an update on an existing agent message (already in agent_messages array),
    // we want to overwrite both the existing entry
    // AND clear all of the subsequent entries (e.g. we have [1, 2, 3, 4], update 2* > messages become [1, 2*])
    // The message may be an array of messages (all one type):
    // e.g. we have [1, 2, 3, 4], update [2*, 3*] > messages become [1, 2*, 3*]
    // if there is not an existing entry, append to end, e.g. we have [1, 2, 3, 4], update 5 > messages become [1, 2, 3, 4, 5]
    // Distinguish entries via "current_id"

    // We can assume (or error otherwise) that we are sending agent messages associated with an already broadcast phase.
    // When an existing phase message is updated with agent message(s), we clear later phases. 
    // e.g. [Phase0: [0] Phase1: [1, 2], Phase2: [2]], update Phase1: [3], our phaseMessages becomes [Phase0: [0], Phase1: [1, 2, 3]]
  }, []);

  const handleUpdatedActionMessage = useCallback((updatedAgentMessage) => {
    console.error("We shouldn't be broadcasting ActionMessages");
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
          console.error(`${message.message_type}: ${message.error}`);
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
  }, [handleUpdatedAgentMessage]);

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
      const wsUrl = `ws://localhost:8000/ws/${workflowId}`;
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
  }, [workflowId, maxReconnectAttempts]);

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
    messages,
    error,
    workflowStatus,
    currentPhase,
  };
};