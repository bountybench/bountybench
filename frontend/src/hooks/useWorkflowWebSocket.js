import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId, interactiveMode) => {
  const [isConnected, setIsConnected] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [pendingUserInput, setPendingUserInput] = useState(null);
  
  const ws = useRef(null);
  const messageIdCounter = useRef(0);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const currentIterationRef = useRef(null);

  // ----------------------------------
  // 1) Connect / Reconnect logic
  // ----------------------------------
  const connect = useCallback(() => {
    if (!workflowId) {
      console.warn('No workflow ID provided, skipping connection');
      return;
    }

    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      setError('Failed to connect after multiple attempts');
      return;
    }

    const wsUrl = `ws://localhost:8000/ws`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected for workflow:', workflowId);
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected for workflow:', workflowId, 'Event:', event);
      setIsConnected(false);
      
      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket error for workflow:', workflowId, 'Event:', event);
      setError('Failed to connect to workflow');
    };

    // ----------------------------------
    // 2) onmessage: handle real-time updates
    // ----------------------------------
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed WebSocket message:', data);

        if (data.workflow_id !== workflowId) {
          console.log('Message not for this workflow, ignoring');
          return;
        }

        switch (data.type) {
          case 'workflow_start':
            setWorkflowStatus('running');
            setMessages(prev => [...prev, {
              id: `msg_${messageIdCounter.current++}`,
              type: 'system',
              content: `Workflow ${data.data.workflow_name} started`,
              timestamp: data.data.start_time
            }]);
            break;

          case 'workflow_complete':
            setWorkflowStatus(data.data.status);
            setMessages(prev => [...prev, {
              id: `msg_${messageIdCounter.current++}`,
              type: 'system',
              content: `Workflow ${data.data.status === 'success' ? 'completed successfully' : 'failed'}`,
              timestamp: data.data.end_time
            }]);
            break;

          case 'phase_start':
            setCurrentPhase(data.data.phase_name);
            setMessages(prev => [...prev, {
              id: `msg_${messageIdCounter.current++}`,
              type: 'system',
              content: `Starting phase: ${data.data.phase_name}`,
              timestamp: data.data.start_time
            }]);
            break;

          case 'phase_complete':
            setMessages(prev => [...prev, {
              id: `msg_${messageIdCounter.current++}`,
              type: 'agent',
              agent_name: data.data.phase_name,
              content: data.data.messages,
              timestamp: data.timestamp,
              success: data.data.success
            }]);
            break;

          case 'request_input':
            if (interactiveMode) {
              setPendingUserInput({
                messageId: data.message_id,
                agentName: data.agent_name,
                message: data.message,
                context: data.context
              });
            }
            break;

          case 'error':
            setError(data.data.error);
            setMessages(prev => [...prev, {
              id: `msg_${messageIdCounter.current++}`,
              type: 'error',
              content: data.data.error,
              phase: data.data.phase,
              timestamp: data.timestamp
            }]);
            break;

          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };
  }, [workflowId, interactiveMode]);

  // ----------------------------------
  // 3) Effect hooks
  // ----------------------------------
  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  // ----------------------------------
  // 4) Message sending functions
  // ----------------------------------
  const sendMessage = useCallback((type, data) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }

    const message = {
      type,
      workflow_id: workflowId,
      ...data
    };

    ws.current.send(JSON.stringify(message));
  }, [workflowId]);

  const sendUserResponse = useCallback((messageId, response) => {
    if (!pendingUserInput || pendingUserInput.messageId !== messageId) {
      console.warn('No pending input request matches this response');
      return;
    }

    sendMessage('agent_response', {
      message_id: messageId,
      response
    });

    setPendingUserInput(null);
  }, [pendingUserInput, sendMessage]);

  return {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    pendingUserInput,
    sendMessage,
    sendUserResponse
  };
};