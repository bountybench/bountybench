import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import './LogViewer.css';

export const LogViewer = ({ workflow }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLogs = async () => {
      if (!workflow?.id) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`http://localhost:8000/workflow/${workflow.id}/logs`);
        if (!response.ok) {
          throw new Error('Failed to fetch logs');
        }
        
        const data = await response.json();
        setLogs(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    // Poll for new logs every 5 seconds
    const interval = setInterval(fetchLogs, 5000);
    
    return () => clearInterval(interval);
  }, [workflow?.id]);

  const renderLogContent = () => {
    if (loading && !logs.length) {
      return (
        <Box display="flex" justifyContent="center" p={2}>
          <CircularProgress size={24} />
        </Box>
      );
    }

    if (error) {
      return <div className="log-error">[ERROR] {error}</div>;
    }

    if (!logs.phases?.length) {
      return <div className="log-info">[INFO] No logs available yet...</div>;
    }

    return logs.phases.map((phase, phaseIndex) => (
      <div key={phaseIndex}>
        <div className="log-phase">[PHASE] {phase.phase_name}</div>
        {phase.iterations.map((iteration, iterIndex) => (
          <div key={iterIndex}>
            <div className="log-iteration">[ITERATION {iteration.iteration_idx}]</div>
            {iteration.actions.map((action, actionIndex) => (
              <div key={actionIndex} className="log-action">
                {action.action_type}: {action.description}
              </div>
            ))}
          </div>
        ))}
      </div>
    ));
  };

  return (
    <Box className="log-container">
      <Typography variant="h6" gutterBottom>
        Workflow Logs
      </Typography>
      <Paper className="log-content">
        {renderLogContent()}
      </Paper>
    </Box>
  );
};
