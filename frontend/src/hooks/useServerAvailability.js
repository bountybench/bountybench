import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config';

const BASE_URL=`http://localhost:7999`

export const useServerAvailability = (onAvailable) => {
  const [serverStatus, setServerStatus] = useState({
    isAvailable: false,
    isChecking: true,
    error: null
  });

  // Store onAvailable callback in a ref so we can call it without triggering re-runs
  const onAvailableRef = useRef(onAvailable);
  const attemptsRef = useRef(0);
  const MAX_ATTEMPTS = 30; // Maximum number of attempts before showing error
  const RETRY_INTERVAL = 1000; // Retry every 1 second

  // Update the ref if onAvailable changes
  useEffect(() => {
    onAvailableRef.current = onAvailable;
  }, [onAvailable]);

  useEffect(() => {
    let timeoutId;

    const checkServer = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/workflow/list`);
        if (response.ok) {
          setServerStatus({
            isAvailable: true,
            isChecking: false,
            error: null
          });
          if (onAvailableRef.current) {
            onAvailableRef.current();
          }
          return true;
        }
      } catch (error) {
        console.error('Server check failed:', error);
      }
      return false;
    };

    const startPolling = async () => {
      setServerStatus(prev => ({ ...prev, isChecking: true }));
      const available = await checkServer();

      // If not available, schedule the next check
      if (!available) {
        attemptsRef.current += 1;
        if (attemptsRef.current >= MAX_ATTEMPTS) {
          setServerStatus({
            isAvailable: false,
            isChecking: false,
            error: "Server is not responding after multiple attempts. Please check if the backend server is running and try again."
          });
        } else {
          timeoutId = setTimeout(startPolling, RETRY_INTERVAL);
        }
      }
    };

    // Start the polling loop once
    startPolling();

    // Cleanup on unmount
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []); // IMPORTANT: empty dependency array → runs only once

  return serverStatus;
};
