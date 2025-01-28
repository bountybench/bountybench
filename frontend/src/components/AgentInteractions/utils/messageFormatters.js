export const formatData = (data) => {
  if (!data) return '';
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data);
      return JSON.stringify(parsed, null, 2); 
    } catch (e) {
      console.error(e);
      return data; 
    }
  }

  if (data.stdout || data.stderr) {
    return `${data.stdout || ''}\n${data.stderr || ''}`.trim();
  }

  try {
    return JSON.stringify(data, null, 2);
  } catch (e) {
    console.error(e);
    return String(data);
  }
};