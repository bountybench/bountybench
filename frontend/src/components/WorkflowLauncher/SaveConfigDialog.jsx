import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Alert } from '@mui/material';

export const SaveConfigDialog = ({ open, onClose, fileName, onFileNameChange, onSave, saveStatus }) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Save Configuration</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="File Name"
          type="text"
          fullWidth
          variant="standard"
          value={fileName}
          onChange={onFileNameChange}
        />
        {saveStatus && (
          <Alert severity={saveStatus.type} sx={{ mt: 2 }}>
            {saveStatus.message}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onSave}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};