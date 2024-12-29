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
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const currentIterationRef = useRef(null);

  console.log('useWorkflowWebSocket state:', { 
    workflowId, 
    isConnected, 
    workflowStatus,
    currentPhase,
    currentIteration,
    messageCount: messages.length,
    reconnectAttempts: reconnectAttempts.current
  });

  const connect = useCallback(() => {
    if (!workflowId) return;

    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      setError('Failed to connect after multiple attempts');
      return;
    }

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
      reconnectAttempts.current = 0;
      
      try {
        const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
          method: 'POST'
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Failed to start workflow execution');
        }
        console.log('Workflow execution started');
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution: ' + err.message);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event);
      setIsConnected(false);
      
      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
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
            console.log('Setting workflow status:', data.status);
            setWorkflowStatus(data.status);
            break;

          case 'phase_update':
            console.log('Setting phase:', data.phase);
            setCurrentPhase(data.phase);
            // Create a message for phase updates
            if (data.phase.status) {
              const phaseMessage = {
                id: `msg_${messageIdCounter.current++}`,
                agent_name: 'System',
                timestamp: new Date().toISOString(),
                input: {
                  content: `Phase ${data.phase.phase_name} ${data.phase.status}`
                },
                isSystem: true
              };
              setMessages(prev => [...prev, phaseMessage]);
            }
            break;

          case 'iteration_update':
            console.log('Setting iteration:', data.iteration);
            setCurrentIteration(data.iteration);
            currentIterationRef.current = data.iteration;
            
            // Create a message for the iteration
            const iterationMessage = {
              id: `msg_${messageIdCounter.current++}`,
              agent_name: data.iteration.agent_name,
              timestamp: new Date().toISOString(),
              input: data.iteration.input,
              output: data.iteration.output,
              actions: [],
              status: data.iteration.status
            };
            setMessages(prev => [...prev, iterationMessage]);
            break;

          case 'action_update':
            console.log('Received action:', data.action);
            // Add the action to the current iteration's message
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1];
              
              // For LLM actions, update the output of the last message
              if (data.action.action_type === 'llm' && data.action.output_data) {
                if (lastMessage) {
                  return [...prev.slice(0, -1), {
                    ...lastMessage,
                    output: {
                      ...lastMessage.output,
                      content: data.action.output_data
                    },
                    actions: [
                      ...(lastMessage.actions || []),
                      {
                        action_type: data.action.action_type,
                        input_data: data.action.input_data,
                        output_data: data.action.output_data,
                        metadata: data.action.metadata,
                        timestamp: data.action.timestamp
                      }
                    ]
                  }];
                }
              }
              
              // If there's no current message or the last message isn't from the current iteration,
              // create a new message for this action
              if (!lastMessage || !lastMessage.actions) {
                return [...prev, {
                  id: `msg_${messageIdCounter.current++}`,
                  agent_name: currentIterationRef.current?.agent_name || 'System',
                  timestamp: data.action.timestamp,
                  actions: [{
                    action_type: data.action.action_type,
                    input_data: data.action.input_data,
                    output_data: data.action.output_data,
                    metadata: data.action.metadata,
                    timestamp: data.action.timestamp
                  }]
                }];
              }
              
              // Add the action to the existing message
              const updatedMessage = {
                ...lastMessage,
                actions: [
                  ...(lastMessage.actions || []),
                  {
                    action_type: data.action.action_type,
                    input_data: data.action.input_data,
                    output_data: data.action.output_data,
                    metadata: data.action.metadata,
                    timestamp: data.action.timestamp
                  }
                ]
              };
              
              return [...prev.slice(0, -1), updatedMessage];
            });
            break;

          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
        setError('Failed to process workflow update: ' + err.message);
      }
    };
  }, [workflowId]);

  useEffect(() => {
    if (workflowId) {
      connect();
      return () => {
        if (ws.current) {
          console.log('Closing WebSocket connection');
          ws.current.close();
        }
      };
    }
  }, [connect, workflowId]);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message);
      ws.current.send(JSON.stringify(message));
      
      // Add user message to the list
      const userMessage = {
        id: `msg_${messageIdCounter.current++}`,
        agent_name: 'User',
        timestamp: new Date().toISOString(),
        input: { content: message.content },
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
