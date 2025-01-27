// components/StatusMessage/StatusMessage.jsx
import React, { useEffect, useState, useRef } from "react";
import { Box, Typography } from '@mui/material';
import './StatusMessage.css'

const StatusMessage = () => {
    const [logs, setLogs] = useState([]);
    const logsEndRef = useRef(null);

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

    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs]);

    return (
        <>
            {logs.length > 0 && (
                <Box className="log-content">
                    {logs.map((log, index) => (
                        <Typography key={index} className="log-text">
                            {log}
                        </Typography>
                    ))}
                    <div ref={logsEndRef} />
                </Box>
            )}
        </>
    );
};

export default StatusMessage;