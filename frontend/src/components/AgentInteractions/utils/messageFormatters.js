export const formatData = (data) => {
  // If data is undefined or null, return an empty string
  if (data == null) return '';

  // If the data is already a string, just return it
  if (typeof data === 'string') {
    return data; 
  }

  // If data is an object with stdout or stderr properties, combine them into a single string
  if (data.stdout || data.stderr) {
    return `${data.stdout || ''}\n${data.stderr || ''}`.trim();
  }

  // Convert other data types to string
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