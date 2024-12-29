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

  // ----------------------------------
  // 1) Connect / Reconnect logic
  // ----------------------------------
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

    // ----------------------------------
    // 2) onmessage: handle real-time updates
    // ----------------------------------
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
            // Create a system message for phase updates
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

          case 'iteration_update': {
            console.log('Setting iteration:', data.iteration);
            setCurrentIteration(data.iteration);
            currentIterationRef.current = data.iteration;

            // ----------------------------------
            // CHANGE: Store iteration_number in the message
            // so we can append actions later
            // ----------------------------------
            const iterationMessage = {
              id: `msg_${messageIdCounter.current++}`,
              iteration_number: data.iteration.iteration_number, // new field
              agent_name: data.iteration.agent_name,
              timestamp: new Date().toISOString(),
              input: data.iteration.input,
              output: data.iteration.output,
              actions: [],
              status: data.iteration.status
            };
            setMessages(prev => [...prev, iterationMessage]);
            break;
          }

          case 'action_update': {
            console.log('Received action:', data.action);
            // ----------------------------------
            // 3) Append action to the correct iteration message
            // ----------------------------------
            setMessages(prev => {
              const updated = [...prev];

              // We'll base iteration_number on currentIterationRef (or it could come from data.action.metadata)
              const iterationNumber = currentIterationRef.current?.iteration_number;

              // Find the existing message that matches this iteration
              const index = updated.findIndex(
                msg => msg.iteration_number === iterationNumber
              );

              if (index === -1) {
                // If no iteration message yet, create a new one
                updated.push({
                  id: `msg_${messageIdCounter.current++}`,
                  iteration_number: iterationNumber,
                  agent_name: currentIterationRef.current?.agent_name || 'System',
                  timestamp: new Date().toISOString(),
                  input: null,
                  output: null,
                  actions: [data.action],
                  status: currentIterationRef.current?.status,
                });
              } else {
                // Update the existing iteration message
                const target = { ...updated[index] };

                // Append the new action
                target.actions = [...(target.actions || []), data.action];

                // If the action is LLM output, update the iteration's "output" field
                if (data.action.action_type === 'llm' && data.action.output_data) {
                  target.output = {
                    content: data.action.output_data
                  };
                }

                updated[index] = target;
              }

              return updated;
            });
            break;
          }

          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
        setError('Failed to process workflow update: ' + err.message);
      }
    };
  }, [workflowId]);

  // ----------------------------------
  // 4) useEffect to initiate connection
  // ----------------------------------
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

  // ----------------------------------
  // 5) sendMessage: for user input
  // ----------------------------------
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

  // ----------------------------------
  // 6) Return relevant state/hooks
  // ----------------------------------
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