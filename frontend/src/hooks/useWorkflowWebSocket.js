import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  
  const ws = useRef(null);
  const messageIdCounter = useRef(0);

  console.log('useWorkflowWebSocket state:', { 
    workflowId, 
    isConnected, 
    workflowStatus,
    currentPhase,
    currentIteration,
    messageCount: messages.length
  });

  const connect = useCallback(() => {
    if (!workflowId) return;

    const wsUrl = `ws://localhost:8000/ws/${workflowId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = async () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
      
      // Start workflow execution
      try {
        const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
          method: 'POST'
        });
        if (!response.ok) {
          throw new Error('Failed to start workflow execution');
        }
        console.log('Workflow execution started');
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution');
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      // Attempt to reconnect after 1 second
      setTimeout(connect, 1000);
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Failed to connect to workflow');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received WebSocket message:', data);

        switch (data.type) {
          case 'status_update':
          case 'initial_state':
            setWorkflowStatus(data.status);
            break;

          case 'phase_update':
            setCurrentPhase(data.phase);
            if (data.phase.status === 'completed') {
              setMessages([]); // Clear messages when phase completes
            }
            break;

          case 'iteration_update':
            setCurrentIteration(data.iteration);
            if (data.iteration.input) {
              const message = {
                id: `msg_${messageIdCounter.current++}`,
                content: data.iteration.input.content,
                agent: data.iteration.agent_name,
                timestamp: new Date().toISOString(),
                isUser: false
              };
              setMessages(prev => [...prev, message]);
            }
            if (data.iteration.output) {
              const message = {
                id: `msg_${messageIdCounter.current++}`,
                content: data.iteration.output.content,
                agent: data.iteration.agent_name,
                timestamp: new Date().toISOString(),
                isUser: false
              };
              setMessages(prev => [...prev, message]);
            }
            break;

          case 'action_update':
            const actionMessage = {
              id: `msg_${messageIdCounter.current++}`,
              content: data.action.action_type,
              metadata: data.action.metadata,
              timestamp: data.action.timestamp,
              isUser: false,
              actions: [{
                type: data.action.action_type,
                description: JSON.stringify(data.action.output_data),
                metadata: data.action.metadata
              }]
            };
            setMessages(prev => [...prev, actionMessage]);
            break;

          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
        setError('Failed to process workflow update');
      }
    };
  }, [workflowId]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        console.log('Closing WebSocket connection');
        ws.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message);
      ws.current.send(JSON.stringify(message));
      
      // Add user message to the list
      const userMessage = {
        id: `msg_${messageIdCounter.current++}`,
        content: message.content,
        timestamp: new Date().toISOString(),
        isUser: true
      };
      setMessages(prev => [...prev, userMessage]);
    } else {
      console.warn('WebSocket not ready for sending');
      setError('Cannot send message: not connected to workflow');
    }
  }, []);

  return {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage
  };
};
