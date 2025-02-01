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