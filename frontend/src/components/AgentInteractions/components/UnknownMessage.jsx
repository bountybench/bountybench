import React, { useState } from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';

const UnknownMessage = ({ message }) => {

  return (
    <Box className="message-container system">
      <Card className="message-bubble system-bubble">
        <CardContent>
          <Typography variant="subtitle2" color="error">
            Unknown message_type: {message.message_type}
          </Typography>
          <pre>{JSON.stringify(message, null, 2)}</pre>
        </CardContent>
      </Card>
    </Box>
  );
};

export default UnknownMessage;