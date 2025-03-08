import React, { useState, useEffect, useMemo } from 'react';
import { Box, Paper, IconButton } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import LogsList from './LogsList';
import LogMainContent from './LogMainContent';
import './LogViewer.css';

const BASE_URL = `http://localhost:7999`;

export const LogViewer = ({ workflow }) => {
  const [logFiles, setLogFiles] = useState([]);
  const [selectedLogContent, setSelectedLogContent] = useState('');
  const [selectedLogFile, setSelectedLogFile] = useState('');
  const [expandedWorkflows, setExpandedWorkflows] = useState({});
  const [expandedCodebases, setExpandedCodebases] = useState({});
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const [logsListOpen, setLogsListOpen] = useState(true);

  // Fetch log file list
  useEffect(() => {
    fetch(`${BASE_URL}/logs`)
      .then((response) => response.json())
      .then((data) => {

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
          { logsListOpen &&
            <LogsList 
              groupedLogs={groupedLogs}
              toggleCodebase={toggleCodebase}
              expandedCodebases={expandedCodebases}
              toggleWorkflow={toggleWorkflow}
              expandedWorkflows={expandedWorkflows}
              handleLogClick={handleLogClick}
              isOpen={logsListOpen}
            />
          }
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