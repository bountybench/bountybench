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
    if (!workflowId) {
      console.warn('No workflow ID provided, skipping connection');
      return;
    }

    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      setError('Failed to connect after multiple attempts');
      return;
    }

    const wsUrl = `ws://localhost:8000/ws/${workflowId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    console.log('Current workflow ID:', workflowId);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = async () => {
      console.log('WebSocket connected for workflow:', workflowId);
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
      
      try {
        console.log('Starting workflow execution for:', workflowId);
        const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
          method: 'POST'
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Failed to start workflow execution');
        }
        console.log('Workflow execution started successfully');
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution: ' + err.message);
      }
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
        console.log('Raw WebSocket message:', event.data);
        console.log('Parsed WebSocket message type:', data.type);
        console.log('Full message data:', data);

        switch (data.type) {
          case 'status_update':
          case 'initial_state':
            console.log('Handling status update:', data.status);
            setWorkflowStatus(data.status);
            break;

          case 'phase_update':
            console.log('Handling phase update:', data.phase);
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
              console.log('Handling iteration update:', data.iteration);
              setCurrentIteration(data.iteration);
              currentIterationRef.current = data.iteration;
            
              const iterationMessage = {
                id: `msg_${messageIdCounter.current++}`,
                iteration_number: data.iteration.iteration_number,
                agent_name: data.iteration.agent_name,
                timestamp: new Date().toISOString(),
                input: data.iteration.input,
                output: data.iteration.output,
                actions: [],
                status: data.iteration.status
              };
            
              setMessages(prev => {
                // Check if a message with the same iteration number already exists
                if (prev.some(msg => msg.iteration_number === iterationMessage.iteration_number)) {
                  console.log('Duplicate iteration message, not adding');
                  return prev;
                }
                return [...prev, iterationMessage];
              });
              break;
          }

          case 'action_update': {
            console.log('Handling action update:', data.action);
            setMessages(prev => {
              const updated = [...prev];
              const iterationNumber = currentIterationRef.current?.iteration_number;
              console.log('Current iteration number:', iterationNumber);
          
              const index = updated.findIndex(
                msg => msg.iteration_number === iterationNumber
              );
          
              if (index === -1) {
                console.warn('No matching iteration found for action:', data.action);
                return prev;
              }
          
              const target = { ...updated[index] };
              
              // Check if this action already exists
              const actionExists = target.actions.some(action => 
                action.timestamp === data.action.timestamp && 
                action.action_type === data.action.action_type
              );
          
              if (actionExists) {
                console.log('Duplicate action, not adding');
                return prev;
              }
          
              target.actions = [...(target.actions || []), data.action];
          
              if (data.action.action_type === 'llm' && data.action.output_data) {
                target.output = {
                  content: data.action.output_data
                };
              }
          
              updated[index] = target;
              return updated;
            });
            break;
          }

          case 'input_edit_update': {
            console.log('Handling input edit update:', data);
            setMessages(prev => {
              const updated = [...prev];
              const iterationNumber = currentIterationRef.current?.iteration_number;
              console.log('Current iteration number:', iterationNumber);
          
              const messageIndex = updated.findIndex(
                msg => msg.iteration_number === iterationNumber
              );
          
              if (messageIndex === -1) {
                console.warn('No matching iteration found for input edit update');
                return prev;
              }
          
              const target = { ...updated[messageIndex] };
              target.actions = target.actions || [];
          
              // Find the existing action
              const actionIndex = target.actions.findIndex(action => action.timestamp === data.action_id);
              
              if (actionIndex !== -1) {
                // Update existing action
                const existingAction = target.actions[actionIndex];
                if (existingAction.input_data === data.new_input && existingAction.output_data === data.new_output) {
                  console.log('No changes in input or output, not updating');
                  return prev;
                }
                target.actions[actionIndex] = {
                  ...existingAction,
                  input_data: data.new_input,
                  output_data: data.new_output
                };
              } else {
                // Add new action
                target.actions.push({
                  id: data.action_id || `action_${target.actions.length}`,
                  input_data: data.new_input,
                  output_data: data.new_output
                });
              }
          
              // Update the output of the message if it's an LLM action
              if (data.new_output) {
                target.output = {
                  content: data.new_output
                };
              }
          
              updated[messageIndex] = target;
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
      ws.current.send(JSON.stringify({
        type: 'user_input',
        content: message.content
      }));
      
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