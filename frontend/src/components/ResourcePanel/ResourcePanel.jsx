import React, { useState, useEffect } from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Collapse, CircularProgress } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import './ResourcePanel.css';

export const ResourcePanel = ({ workflow }) => {
  const [openFolders, setOpenFolders] = useState({});
  const [resources, setResources] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResources = async () => {
      if (!workflow?.id) return;

      try {
        const response = await fetch(`http://localhost:8000/workflow/${workflow.id}/resources`);
        if (!response.ok) {
          throw new Error('Failed to fetch resources');
        }
        const data = await response.json();
        setResources(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResources();
  }, [workflow]);
  

  const toggleFolder = (path) => {
    setOpenFolders(prev => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  const renderResourceTree = (resources, path = '') => {
    return resources?.map((resource, index) => {
      const fullPath = path ? `${path}/${resource.name}` : resource.name;
      const isFolder = resource.type === 'directory';
      const indentLevel = path.split('/').length;

      return (
        <React.Fragment key={fullPath}>
          <ListItem 
            button 
            onClick={() => isFolder && toggleFolder(fullPath)}
            className="resource-item"
            style={{ paddingLeft: `${indentLevel * 16}px` }}
          >
            <ListItemIcon className="resource-icon">
              {isFolder ? <FolderIcon color="primary" /> : <DescriptionIcon color="info" />}
            </ListItemIcon>
            <ListItemText 
              primary={resource.name}
              secondary={!isFolder ? `${(resource.size / 1024).toFixed(1)} KB` : ''}
              className="resource-text"
            />
            {isFolder && (openFolders[fullPath] ? <ExpandLess /> : <ExpandMore />)}
          </ListItem>
          {isFolder && (
            <Collapse in={openFolders[fullPath]} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {renderResourceTree(resource.children, fullPath)}
              </List>
            </Collapse>
          )}
        </React.Fragment>
      );
    });
  };

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  return (
    <Box className="resources-container">
      <Typography variant="h6" gutterBottom>
        Resources
      </Typography>
      <List dense className="resources-list">
        {renderResourceTree([
          {
            name: 'exploit_files',
            type: 'directory',
            children: []
          },
          {
            name: 'patch_files',
            type: 'directory',
            children: []
          }
        ])}
      </List>
    </Box>
  );
};

//   return (
//     <Box className="resources-container">
//       <Typography variant="h6" gutterBottom>
//         Resources
//       </Typography>
//       <List dense className="resources-list">
//         {renderResourceTree(resources)}
//       </List>
//     </Box>
//   );
// };