// components/StatusMessage/StatusMessage.jsx
import React, { useEffect, useState } from "react";
import { Box, Typography } from '@mui/material';
import './StatusMessage.css'

const StatusMessage = () => {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws/logs");

        ws.onmessage = (event) => {
            setLogs((prevLogs) => [...prevLogs, event.data]);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed");
        };

        return () => ws.close();
    }, []);

    return (
        <>
            {logs.length > 0 && (
                <Box className="log-content">
                    {logs.map((log, index) => (
                        <Typography key={index} className="log-text">
                            {log}
                        </Typography>
                    ))}
                </Box>
            )}
        </>
    );
};

export default StatusMessage;