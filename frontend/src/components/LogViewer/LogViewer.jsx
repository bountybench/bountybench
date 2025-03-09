import React, { useState, useEffect, useMemo } from 'react';
import { Box, Paper, IconButton, FormControlLabel, Checkbox, Typography, Collapse } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import LogsList from './LogsList';
import LogMainContent from './LogMainContent';
import './LogViewer.css';

const BASE_URL = `http://localhost:7999`;

export const LogViewer = () => {
  const [logFiles, setLogFiles] = useState([]);
  const [selectedLogContent, setSelectedLogContent] = useState('');
  const [selectedLogFile, setSelectedLogFile] = useState('');
  const [expandedGroups, setExpandedGroups] = useState({});
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const [logsListOpen, setLogsListOpen] = useState(true);
  const [sortOptionsExpanded, setSortOptionsExpanded] = useState(false);
  const [groupByWorkflow, setGroupByWorkflow] = useState(true);
  const [groupByTaskId, setGroupByTaskId] = useState(false);
  const [onlyShowComplete, setOnlyShowComplete] = useState(false);
  const [onlyShowSuccess, setOnlyShowSuccess] = useState(false);
  
  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${BASE_URL}/logs`);
      const data = await response.json();
      if (Array.isArray(data)) {
        setLogFiles(data);
      } else {
        console.error("Expected an array but got:", data);
        setLogFiles([]);
      }
    } catch (error) {
      console.error('Error fetching log files:', error);
      setLogFiles([]);
    }
  };

  // Fetch log file content  
  const handleLogClick = async (filename) => {
    setLoading(true);
    setSelectedLogFile(filename);
    try {
      const response = await fetch(`${BASE_URL}/logs/${filename}`);
      const content = await response.json();

      // Construct current_children for PhaseMessage
      const modifiedContent = content?.phase_messages?.map(phase => {
        if (phase.agent_messages) {

          phase.agent_messages = phase.agent_messages.map(agentMessage => ({
            ...agentMessage,
            current_children: agentMessage.action_messages || []
          }));
        }
        return phase;
      });
      
      setSelectedLogContent(modifiedContent || null);
    } catch (error) {
      console.error('Error fetching log content:', error);
    } finally {
      setLoading(false);
    }
  };

  const groupedLogs = useMemo(() => {
    const filtered = logFiles.filter(file => 
      (!onlyShowComplete || file.complete) && 
      (!onlyShowSuccess || file.success)
    );

    const grouped = {};
  
    filtered.forEach((file) => {
      let primaryKey = groupByWorkflow ? file.workflow_name : 'All Workflows';
      let secondaryKey = groupByTaskId ? file.task_id : 'All Tasks';
  
      if (!grouped[primaryKey]) {
        grouped[primaryKey] = {};
      }
      
      if (!grouped[primaryKey][secondaryKey]) {
        grouped[primaryKey][secondaryKey] = [];
      }
  
      grouped[primaryKey][secondaryKey].push(file);
    });

    // Sort the files within each group alphabetically by filename
    Object.keys(grouped).forEach(primaryKey => {
      Object.keys(grouped[primaryKey]).forEach(secondaryKey => {
        grouped[primaryKey][secondaryKey].sort((a, b) => a.filename.localeCompare(b.filename));
      });
    });

    return grouped;
  }, [logFiles, groupByWorkflow, groupByTaskId, onlyShowComplete, onlyShowSuccess]);


  const toggleGroup = (group) => {
    setExpandedGroups(prev => ({
      ...prev,
      [group]: !prev[group]
    }));
  };

  const handleRerunMessage = (messageId) => {
    console.log(`Rerun placeholder for message ID: ${messageId}`);
    // TODO: Implement rerun logic
  };
  
  const handleUpdateMessageInput = (messageId) => {
    console.log(`Update placeholder for message ID: ${messageId}`);
    // TODO: Implement update logic
  };

  const toggleLogsList = () => {
    setLogsListOpen(!logsListOpen);
  };

  return (
    <Box className="log-container">
      <Paper className="log-content">
        <Box className="log-main-layout">
          {logsListOpen && (
            <Box className="log-sidebar">
              <Box className="sort-options">
                <Typography
                  variant="subtitle2"
                  onClick={() => setSortOptionsExpanded(!sortOptionsExpanded)}
                  className="sort-by-label"
                >
                  Sort by {sortOptionsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                </Typography>
                <Collapse in={sortOptionsExpanded}>
                  <Box className="sort-options-grid">
                    <FormControlLabel
                      control={<Checkbox checked={groupByWorkflow} onChange={(e) => setGroupByWorkflow(e.target.checked)} size="small" />}
                      label="Workflow"
                      className="sort-option-label"
                    />
                    <FormControlLabel
                      control={<Checkbox checked={groupByTaskId} onChange={(e) => setGroupByTaskId(e.target.checked)} size="small" />}
                      label="Task ID"
                      className="sort-option-label"
                    />
                    <FormControlLabel
                      control={<Checkbox checked={onlyShowComplete} onChange={(e) => setOnlyShowComplete(e.target.checked)} size="small" />}
                      label="Complete"
                      className="sort-option-label"
                    />
                    <FormControlLabel
                      control={<Checkbox checked={onlyShowSuccess} onChange={(e) => setOnlyShowSuccess(e.target.checked)} size="small" />}
                      label="Successful"
                      className="sort-option-label"
                    />
                  </Box>
                </Collapse>
              </Box>
              <LogsList 
                groupedLogs={groupedLogs}
                expandedGroups={expandedGroups}
                toggleGroup={toggleGroup}
                handleLogClick={handleLogClick}
                groupByWorkflow={groupByWorkflow}
                groupByTaskId={groupByTaskId}
              />
            </Box>
          )}
          <IconButton onClick={toggleLogsList} className="logsList-toggle" size="small">
            {logsListOpen ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </IconButton>
          <LogMainContent 
            selectedLogFile={selectedLogFile}
            loading={loading}
            selectedLogContent={selectedLogContent}
            isEditing={isEditing}
            setIsEditing={setIsEditing}
            selectedCellId={selectedCellId}
            setSelectedCellId={setSelectedCellId}
            handleRerunMessage={handleRerunMessage}
            handleUpdateMessageInput={handleUpdateMessageInput}
          />
        </Box>
      </Paper>
    </Box>
  );
};

export default LogViewer;