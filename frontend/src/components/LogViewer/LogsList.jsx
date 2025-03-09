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
                {Object.entries(secondaryGroups).map(([secondaryGroup, files]) => (
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
                        {files.map((file) => (
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