// LogsList.jsx
import React from 'react';
import { Box, Typography, List, ListItem, ListItemText, ListItemButton, Collapse } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';

const LogsList = ({ 
  groupedLogs, 
  expandedGroups,
  toggleGroup,
  handleLogClick,
  groupByWorkflow,
  groupByTaskId
}) => {
  const getDisplayName = (file) => {
    let displayName = file.filename.split('_').slice(-2).join('_').slice(0, -5);
    
    if (!groupByWorkflow) {
      displayName = `${file.workflow_name} - ${displayName}`;
    }
    
    if (!groupByTaskId) {
      // Remove 'bountybench/' from the beginning of task_id if it exists
      const cleanTaskId = file.task_id.startsWith('bountybench/') 
        ? file.task_id.slice('bountybench/'.length) 
        : file.task_id;
      displayName = `${cleanTaskId} - ${displayName}`;
    }
    
    return displayName;
  };

  const getDateTimeFromFilename = (filename) => {
    const parts = filename.split('_');
    const datePart = parts[parts.length - 2];
    const timePart = parts[parts.length - 1].split('.')[0];
    
    const [year, month, day] = datePart.split('-');
    const [hours, minutes, seconds] = timePart.split('-');
    
    // JavaScript months are 0-indexed, so we subtract 1 from the month
    return new Date(year, month - 1, day, hours, minutes, seconds);
  };

  const sortFiles = (files) => {
    return files.sort((a, b) => {
      if (!groupByWorkflow && !groupByTaskId) {
        // Sort by date/time descending when not grouping
        return getDateTimeFromFilename(b.filename) - getDateTimeFromFilename(a.filename);
      }
      
      if (!groupByWorkflow) {
        // Sort by workflow name, then date/time descending
        if (a.workflow_name !== b.workflow_name) {
          return a.workflow_name.localeCompare(b.workflow_name);
        }
      }
      
      if (!groupByTaskId) {
        // Sort by task ID, then date/time descending
        if (a.task_id !== b.task_id) {
          return a.task_id.localeCompare(b.task_id);
        }
      }
      
      // Default to sorting by date/time descending
      return getDateTimeFromFilename(b.filename) - getDateTimeFromFilename(a.filename);
    });
  };


  return (
    <Box className="log-sidebar-content">
      <Typography variant='subtitle1' className='log-sidebar-title'>
        Log History
      </Typography>
      <List>
        {Object.entries(groupedLogs).map(([primaryGroup, secondaryGroups]) => (
          <React.Fragment key={primaryGroup}>
            {groupByWorkflow && (
              <ListItem button onClick={() => toggleGroup(primaryGroup)}>
                <ListItemText
                  primary={
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                      {primaryGroup}
                    </Typography>
                  }
                />
                {expandedGroups[primaryGroup] ? <ExpandLess /> : <ExpandMore />}
              </ListItem>
            )}

            <Collapse in={groupByWorkflow ? expandedGroups[primaryGroup] : true} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {Object.entries(secondaryGroups).sort(([a], [b]) => a.localeCompare(b)).map(([secondaryGroup, files]) => (
                  <React.Fragment key={secondaryGroup}>
                    {groupByTaskId && (
                      <ListItemButton sx={{ pl: groupByWorkflow ? 4 : 2 }} onClick={() => toggleGroup(`${primaryGroup}_${secondaryGroup}`)}>
                        <ListItemText
                          primary={
                            <Typography variant="body1" className='codebase-text'>
                              {secondaryGroup}
                            </Typography>
                          }
                        />
                        {expandedGroups[`${primaryGroup}_${secondaryGroup}`] ? <ExpandLess /> : <ExpandMore />}
                      </ListItemButton>
                    )}

                    <Collapse in={groupByTaskId ? expandedGroups[`${primaryGroup}_${secondaryGroup}`] : true} timeout="auto" unmountOnExit>
                      <List component="div" disablePadding>
                        {sortFiles(files).map((file) => (
                          <ListItemButton 
                            key={file.filename} 
                            sx={{ pl: groupByWorkflow && groupByTaskId ? 6 : groupByWorkflow || groupByTaskId ? 4 : 2 }} 
                            onClick={() => handleLogClick(file.filename)}
                          >
                            <ListItemText
                              primary={
                                <Typography 
                                  variant="body2" 
                                  className='codebase-item-text'
                                  style={{ color: file.success ? '#a9ffbc' : 'inherit', fontWeight: file.success ? 'bold' : 'normal' }}
                                >
                                  {getDisplayName(file)}
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
  );
};

export default LogsList;