export const formatData = (data) => {
  // If data is undefined or null, return an empty string
  if (data == null) return '';

  // If the data is already a string, attempt to parse JSON for pretty printing, else return raw string
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return data;
    }
  }

  // If data is an object with stdout or stderr properties, combine them
  if (data && typeof data === 'object' && (data.stdout || data.stderr)) {
    return `${data.stdout || ''}\n${data.stderr || ''}`.trim();
  }

  // If data is an object, pretty print as JSON
  if (data && typeof data === 'object') {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }

  // Fallback for other types
  return String(data);
};

export const formatTimeElapsed = (data) => {
  const ms = Number(data);
  
  if (isNaN(ms)) {
    return null;
  }
  
  // Convert to seconds
  let totalSeconds = ms / 1000;
  
  const hours = Math.floor(totalSeconds / 3600);
  totalSeconds %= 3600;
  const minutes = Math.floor(totalSeconds / 60);
  totalSeconds %= 60;
  const seconds = totalSeconds.toFixed(2);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
};