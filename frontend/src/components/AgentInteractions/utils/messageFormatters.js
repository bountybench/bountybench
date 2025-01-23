export const formatData = (data) => {
  if (!data) return '';
  if (typeof data === 'string') return data;

  if (data.stdout || data.stderr) {
    return `${data.stdout || ''}\n${data.stderr || ''}`.trim();
  }
  
  try {
    if (typeof data === 'string') {
      const parsed = JSON.parse(data);
      return JSON.stringify(parsed, null, 2);
    }
    return JSON.stringify(data, null, 2);
  } catch (e) {
    return String(data);
  }
};