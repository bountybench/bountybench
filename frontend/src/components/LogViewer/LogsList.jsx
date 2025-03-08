import React from 'react';
import { Box, Typography, List, ListItem, ListItemText, ListItemButton, Collapse } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';

const LogsList = ({ 
  groupedLogs, 
  toggleCodebase,
  expandedCodebases,
  toggleWorkflow,
  expandedWorkflows,
  handleLogClick, 
  isOpen 
}) => {

  return (
    <Box className={`log-sidebar-container ${isOpen ? 'open' : 'closed'}`}>
      <Typography variant='subtitle1' className='log-sidebar-title'>
        Log History
      </Typography>
      <List>
        {Object.keys(groupedLogs).sort().map((workflow) => (
          <React.Fragment key={workflow}>
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
  );
};

export default LogsList;