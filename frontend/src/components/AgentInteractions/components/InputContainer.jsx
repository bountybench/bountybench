import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, Button } from '@mui/material';

const InputContainer = ({ onSendMessage }) => {
  const [userMessage, setUserMessage] = useState('');
  const [textAreaHeight, setTextAreaHeight] = useState('auto');
  const textAreaRef = useRef(null);

  useEffect(() => {
    adjustTextAreaHeight();
  }, [userMessage]);

  const adjustTextAreaHeight = () => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
      const newHeight = Math.min(textAreaRef.current.scrollHeight, window.innerHeight * 0.4);
      textAreaRef.current.style.height = `${newHeight}px`;
      setTextAreaHeight(`${newHeight}px`);
    }
  };

  const handleSendMessage = () => {
    if (userMessage.trim()) {
      onSendMessage({
        type: 'user_message',
        content: userMessage
      });
      setUserMessage('');
    }
  };

  return (
    <Box className="input-container">
      <TextField
        fullWidth
        multiline
        inputRef={textAreaRef}
        rows={2}
        variant="outlined"
        placeholder="Type your message..."
        value={userMessage}
        onChange={(e) => setUserMessage(e.target.value)}
        sx={{ 
          '& .MuiInputBase-input': {
            color: 'black',
            height: textAreaHeight,
            minHeight: '25px',
            overflow: 'auto',
          },
          border: '1px solid #ccc',
          borderRadius: '6px',
        }}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
          }
        }}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={handleSendMessage}
        disabled={!userMessage.trim()}
      >
        Send
      </Button>
    </Box>
  );
};

export default InputContainer;