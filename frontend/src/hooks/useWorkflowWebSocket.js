import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
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

  const handleUpdatedAgentMessage = useCallback((updatedAgentMessage) => {
    setMessages((prevMessages) => {
      const index = prevMessages.findIndex(
        (msg) => msg.current_id === updatedAgentMessage.current_id
      );

      if (index !== -1) {
        const newMessages = [...prevMessages];
        newMessages[index] = updatedAgentMessage;
        return newMessages;
      } else {
        return [...prevMessages, updatedAgentMessage];
      }
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

      switch (data.message_type) {
        case 'connection_established':
          connectionEstablished.current = true;
          setIsConnected(true);
          break;

        case 'workflow_status':
          console.log(`Received workflow status update: ${data.status}`);
          setWorkflowStatus(data.status);
          if (data.error) {
            console.error(`Workflow error: ${data.error}`);
            setError(data.error);
          }
          break;

        case 'WorkflowMessage':
          setMessages((prev) => [...prev, data]);
          if (data.workflow_metadata?.workflow_summary) {
            setWorkflowStatus(data.workflow_metadata.workflow_summary);
          }
          break;

        case 'PhaseMessage':
          setCurrentPhase(data);
          setMessages((prev) => {
            const idx = prev.findIndex((msg) => msg.current_id === data.current_id);
            if (idx > -1) {
              const newArr = [...prev];
              newArr[idx] = data;
              return newArr;
            } else {
              return [...prev, data];
            }
          });
          break;

        case 'AgentMessage':
          handleUpdatedAgentMessage(data);
          break;

        case 'ActionMessage':
          setMessages((prev) => [...prev, data]);
          break;

        case 'first_message':
          setMessages((prev) => [...prev, data]);
          break;

        case 'workflow_completed':
          setWorkflowStatus('completed');
          setMessages(prev => [...prev, data]);
          break;

        default:
          console.warn('Unknown message_type:', data.message_type);
          setMessages((prev) => [...prev, data]);
      }
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

  const sendMessage = useCallback((message) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN || !connectionEstablished.current) {
      console.warn('WebSocket not ready for sending');
      setError('Cannot send message: not connected to workflow');
      return;
    }

    try {
      ws.current.send(
        JSON.stringify({
          message_type: 'user_message',
          content: message.content
        })
      );
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message: ' + err.message);
    }
  }, []);

  return {
    isConnected,
    messages,
    error,
    workflowStatus,
    currentPhase,
    sendMessage
  };
};