import React, { useState, useEffect, useMemo } from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemText,ListItemButton,  Collapse } from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import PhaseMessage from '../AgentInteractions/components/PhaseMessage/PhaseMessage.jsx';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import './LogViewer.css';

export const LogViewer = ({ workflow }) => {
  const [logFiles, setLogFiles] = useState([]);
  const [selectedLogContent, setSelectedLogContent] = useState('');
  const [selectedLogFile, setSelectedLogFile] = useState('');
  const [expandedWorkflows, setExpandedWorkflows] = useState({});
  const [expandedCodebases, setExpandedCodebases] = useState({});
  const [loading, setLoading] = useState(false);

  // Fetch log file list
  useEffect(() => {
    fetch('http://localhost:8000/logs')
      .then((response) => response.json())
      .then((data) => {
        console.log("Fetched log files:", data);
        if (Array.isArray(data)) {
          setLogFiles(data);
        } else {
          console.error("Expected an array but got:", data);
          setLogFiles([]);
        }
      })
      .catch((error) => {
        console.error('Error fetching log files:', error);
        setLogFiles([]); 
      });
  }, []);
  

  // Fetch log file content
  const handleLogClick = async (filename) => {
    setLoading(true);
    setSelectedLogFile(filename);
    console.log("file read");
    try {
      const response = await fetch(`http://localhost:8000/logs/${filename}`);
      const content = await response.json();
      setSelectedLogContent(content?.phase_messages || null);
    } catch (error) {
      console.error('Error fetching log content:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Function to group logs by workflow type and codebase
  const groupedLogs = useMemo(() => {
    const grouped = {};
  
    logFiles.forEach((file) => {
      const rawWorkflowType = file.split('_')[0];
      const workflowType = rawWorkflowType.slice(0, -8); 
      const codebase = file.split('_')[1];
  
      if (!grouped[workflowType]) {
        grouped[workflowType] = {};
      }
  
      if (!grouped[workflowType][codebase]) {
        grouped[workflowType][codebase] = [];
      }
  
      grouped[workflowType][codebase].push(file);
    });
    console.log("loading groups");
    return grouped;
  }, [logFiles]);

  // Toggle functions for expanding/collapsing groups
  const toggleWorkflow = (workflow) => {
    setExpandedWorkflows((prev) => ({ 
      ...prev, 
      [workflow]: !prev[workflow] 
    }));
  };

  const toggleCodebase = (workflow, codebase) => {
    setExpandedCodebases((prev) => ({
      ...prev,
      [`${workflow}_${codebase}`]: !prev[`${workflow}_${codebase}`],
    }));
  };

  
  return (
    <Box className="log-container">
      <Paper className="log-content">
        <Box className="log-main-layout">
          {/* Sidebar */}
          <Box className="log-sidebar-container">
            <Typography variant='subtitle1' className='log-sidebar-title'>
              Log History
            </Typography>
            <List>
              {Object.keys(groupedLogs).sort().map((workflow) => (
                <React.Fragment key={workflow}>
                  {/* Workflow Type */}
                  <ListItem button onClick={() => toggleWorkflow(workflow)}>
                    <ListItemText
                      primary={
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                          {workflow}
                        </Typography>
                      }
                    />
                    {expandedWorkflows[workflow] ? <ExpandLess /> : <ExpandMore />}
                  </ListItem>

                  <Collapse in={expandedWorkflows[workflow]} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      {Object.keys(groupedLogs[workflow]).sort().map((codebase) => (
                        <React.Fragment key={`${workflow}_${codebase}`}>
                          {/* Codebase */}
                          <ListItemButton sx={{ pl: 2 }} onClick={() => toggleCodebase(workflow, codebase)} >
                            <ListItemText
                              primary={
                                <Typography variant="body1" className='codebase-text'>
                                  {codebase}
                                </Typography>
                              }
                            />
                            {expandedCodebases[`${workflow}_${codebase}`] ? <ExpandLess /> : <ExpandMore />}
                          </ListItemButton>

                          <Collapse in={expandedCodebases[`${workflow}_${codebase}`]} timeout="auto" unmountOnExit>
                            <List component="div" disablePadding>
                              {groupedLogs[workflow][codebase].map((file) => (
                                <ListItemButton key={file} sx={{ pl: 4 }} onClick={() => handleLogClick(file)}>
                                  <ListItemText
                                    primary={
                                      <Typography variant="body2" className='codebase-item-text'>
                                        {file.split('_')[0] === 'ChatWorkflow'
                                        ? file.split('_').slice(-2).join('_').slice(0, -5)
                                        : file.split('_').slice(-3).join('_').slice(0, -5)}
                                      </Typography>
                                    }
                                  />
                                </ListItemButton>
                              ))}
                            </List>
                          </Collapse>
                        </React.Fragment>
                      ))}
                    </List>
                  </Collapse>
                </React.Fragment>
              ))}
            </List>
          </Box>
  
          {/* Main Content */}
          <Box className="log-main-container">
            <Typography variant="subtitle1" gutterBottom>
              {selectedLogFile ? `Viewing ${selectedLogFile}` : 'Pick a log file to view.'}
            </Typography>
            {loading && (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
              </Box>
            )}
            {!loading && selectedLogContent && (
              <Box className="log-item-container">
                {selectedLogContent.map((phase, index) => (
                  <PhaseMessage
                    key={index}
                    message={{
                      phase_name: phase.phase_id,
                      phase_summary: phase.phase_summary,
                      current_children: phase.agent_messages || [],
                      additional_metadata: phase.additional_metadata || null,
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};
export default LogViewer;