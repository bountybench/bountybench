import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (initialWorkflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [workflowId, setWorkflowId] = useState(initialWorkflowId);
  
  const ws = useRef(null);
  const messageIdCounter = useRef(0);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const currentIterationRef = useRef(null);

  // Update workflowId when initialWorkflowId changes
  useEffect(() => {
    setWorkflowId(initialWorkflowId);
  }, [initialWorkflowId]);

  console.log('useWorkflowWebSocket state:', { 
    workflowId, 
    initialWorkflowId,
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
  const setupWebSocketHandlers = useCallback((websocket) => {
    websocket.onopen = async () => {
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

    websocket.onclose = (event) => {
      console.log('WebSocket disconnected for workflow:', workflowId, 'Event:', event);
      setIsConnected(false);
      
      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
    };

    websocket.onerror = (event) => {
      console.error('WebSocket error for workflow:', workflowId, 'Event:', event);
      setError('Failed to connect to workflow');
    };

    websocket.onmessage = (event) => {
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
            
              setMessages(prev => {
                const updatedMessages = [...prev];
                const existingMessageIndex = updatedMessages.findIndex(
                  msg => msg.iteration_number === data.iteration.iteration_number
                );
            
                const updatedMessage = {
                  id: existingMessageIndex !== -1 ? updatedMessages[existingMessageIndex].id : `msg_${messageIdCounter.current++}`,
                  iteration_number: data.iteration.iteration_number,
                  agent_name: data.iteration.agent_name,
                  timestamp: new Date().toISOString(),
                  input: data.iteration.input || updatedMessages[existingMessageIndex]?.input,
                  output: data.iteration.output,
                  actions: updatedMessages[existingMessageIndex]?.actions || [],
                  status: data.iteration.status
                };
            
                if (existingMessageIndex !== -1) {
                  updatedMessages[existingMessageIndex] = updatedMessage;
                } else {
                  updatedMessages.push(updatedMessage);
                }
            
                return updatedMessages;
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
      } catch (error) {
        console.error('Error handling WebSocket message:', error);
      }
    };
  }, [workflowId]);

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
    setupWebSocketHandlers(ws.current);
  }, [workflowId, setupWebSocketHandlers]);

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
  // 5) sendMessage: for user message
  // ----------------------------------
  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message);
      ws.current.send(JSON.stringify({
        type: 'user_message',
        content: message.content
      }));
      
      // Add user message to the list
      const userMessage = {
        id: `msg_${messageIdCounter.current++}`,
        agent_name: 'User',
        timestamp: new Date().toISOString(),
        output: { content: message.content },
        isUser: true
      };
      setMessages(prev => [...prev, userMessage]);
    } else {
      console.warn('WebSocket not ready for sending');
      setError('Cannot send message: not connected to workflow');
    }
  }, []);

  // ----------------------------------
  // 6) restartWorkflow: for restarting workflow
  // ----------------------------------
  const restartWorkflow = useCallback(async () => {
    if (!workflowId) {
      console.warn('No workflow ID provided');
      return;
    }

    try {
      // Close existing WebSocket connection
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.close();
      }

      // Call restart endpoint
      const response = await fetch(`http://localhost:8000/workflow/restart/${workflowId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to restart workflow');
      }

      const data = await response.json();
      
      // Reset state
      setMessages([]);
      setCurrentPhase(null);
      setCurrentIteration(null);
      setWorkflowStatus(null);
      currentIterationRef.current = null;
      
      // Update workflow ID and reconnect WebSocket with new ID
      const newWorkflowId = data.workflow_id;
      console.log('Restarting workflow with new ID:', newWorkflowId);
      
      // Update the workflow ID state
      setWorkflowId(newWorkflowId);
      
      // Wait a short moment before reconnecting to ensure cleanup is complete
      setTimeout(() => {
        // Update URL with new workflow ID
        window.history.replaceState(null, '', `/workflow/${newWorkflowId}`);
        
        // Reconnect WebSocket with new ID
        ws.current = new WebSocket(`ws://localhost:8000/ws/${newWorkflowId}`);
        setupWebSocketHandlers(ws.current);
        
        // Start workflow execution
        fetch(`http://localhost:8000/workflow/execute/${newWorkflowId}`, {
          method: 'POST'
        }).catch(err => {
          console.error('Failed to execute restarted workflow:', err);
          setError('Failed to execute restarted workflow: ' + err.message);
        });
      }, 500);
      
    } catch (err) {
      console.error('Failed to restart workflow:', err);
      setError('Failed to restart workflow: ' + err.message);
    }
  }, [workflowId, setupWebSocketHandlers]);

  // ----------------------------------
  // 7) Return relevant state/hooks
  // ----------------------------------
  return {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage,
    restartWorkflow,
    workflowId
  };
};