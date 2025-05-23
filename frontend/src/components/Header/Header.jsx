import React from 'react';
import { AppBar, Toolbar, Typography, Switch, FormControlLabel, Box } from '@mui/material';
import './Header.css';

export const Header = ({ onInteractiveModeToggle, interactiveMode }) => {
  return (
    <AppBar position="static" className="header">
      <Toolbar>
        <Typography variant="h6" component="div" className="header-title">
          BountyBench Workflow
        </Typography>
        <Box>
          <FormControlLabel
            control={
              <Switch
                checked={interactiveMode}
                onChange={onInteractiveModeToggle}
                color="secondary"
              />
            }
            label="Interactive Mode"
          />
        </Box>
      </Toolbar>
    </AppBar>
  );
};
