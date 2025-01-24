import { useState, useEffect, useRef } from 'react';

export const useServerAvailability = (onAvailable) => {
  const [isServerAvailable, setIsServerAvailable] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // Store onAvailable callback in a ref so we can call it without triggering re-runs
  const onAvailableRef = useRef(onAvailable);

  // Update the ref if onAvailable changes
  useEffect(() => {
    onAvailableRef.current = onAvailable;
  }, [onAvailable]);

  useEffect(() => {
    let timeoutId;

    const checkServer = async () => {
      try {
        const response = await fetch('http://localhost:8000/workflow/list');
        if (response.ok) {
          setIsServerAvailable(true);
          setIsChecking(false);

          // Call the latest onAvailable callback if defined
          if (onAvailableRef.current) {
            onAvailableRef.current();
          }
          return true;
        }
      } catch (error) {
        // If fetch fails or response not OK, we assume server is still not available
        setIsServerAvailable(false);
      }
      return false;
    };

    const startPolling = async () => {
      setIsChecking(true);
      const available = await checkServer();

      // If not available, schedule the next check
      if (!available) {
        timeoutId = setTimeout(startPolling, 100);
      }
    };

    // Start the polling loop once
    startPolling();

    // Cleanup on unmount
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []); // IMPORTANT: empty dependency array → runs only once

  return { isServerAvailable, isChecking };
};
