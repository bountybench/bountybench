import React from 'react';
import {
  TextField,
  MenuItem,
  Grid,
  Box,
  Button,
  IconButton,
  InputAdornment,
  Divider,
  Alert,
  Typography
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ListIcon from '@mui/icons-material/List';

export const ModelSelectionSection = ({
  formData,
  handleInputChange,
  topLevelSelection,
  handleTopLevelChange,
  selectedModels,
  apiKeys,
  isCustomApiKey,
  setIsCustomApiKey,
  showApiKey,
  handleRevealToggle,
  handleApiKeyChange,
  apiStatus
}) => {
  return (
    <>
      <TextField
        select
        fullWidth
        label="Model Type"
        name="type"
        value={topLevelSelection}
        onChange={handleTopLevelChange}
        margin="normal"
      >
        <MenuItem value="HELM">HELM</MenuItem>
        <MenuItem value="Non-HELM">Non-HELM</MenuItem>
      </TextField>

      {selectedModels && (
        <TextField
          select
          fullWidth
          label="Model Name"
          name="model"
          value={formData.model}
          onChange={handleInputChange}
          margin="normal"
        >
          {selectedModels.map((model) => (
            <MenuItem key={model.name} value={model.name}>
              <Box display="flex" flexDirection="column">
                <Typography>{model.name}</Typography>
              </Box>
            </MenuItem>
          ))}
        </TextField>
      )}

<Grid container spacing={2}>
        <Grid item xs={6}>
          <TextField
            fullWidth
            type="number"
            label="Max Input Tokens"
            name="max_input_tokens"
            value={formData.max_input_tokens || ''}
            onChange={handleInputChange}
            margin="normal"
            helperText="Leave blank for model default"
            InputProps={{
              inputProps: { min: 1 }
            }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            fullWidth
            type="number"
            label="Max Output Tokens" 
            name="max_output_tokens"
            value={formData.max_output_tokens || ''}
            onChange={handleInputChange}
            margin="normal"
            helperText="Leave blank for model default"
            InputProps={{
              inputProps: { min: 1 }
            }}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2} alignItems="center">
        <Grid item xs={5}>
          <TextField
            select={!isCustomApiKey}
            fullWidth
            label="API Key Name"
            name="api_key_name"
            value={formData.api_key_name || ""}
            onChange={handleInputChange}
            required
            margin="normal"
            InputProps={{
              endAdornment: (
                <IconButton onClick={() => {
                  if (isCustomApiKey) {
                    setIsCustomApiKey(!isCustomApiKey);
                    handleInputChange({
                      target: {
                        name: "api_key_name",
                        value: "HELM_API_KEY",
                      },
                    });
                  }
                }}>
                  {isCustomApiKey ? <ListIcon /> : null}
                </IconButton>
              )
            }}
          >
            {Object.keys(apiKeys).map((key) => (
              <MenuItem key={key} value={key}>
                {key}
              </MenuItem>
            ))}
            <Divider />
            <MenuItem onClick={() => {
              setIsCustomApiKey(true);
              handleInputChange({
                target: {
                  name: "api_key_name",
                  value: "my_custom_key",
                },
              });
            }}>
              Enter a New API Key:
            </MenuItem>
          </TextField>
        </Grid>

        <Grid item xs={5.5}>
          <TextField
            fullWidth
            type={showApiKey ? 'text' : 'password'}
            label="API Key Value"
            name="api_key_value"
            value={formData.api_key_value}
            onChange={handleInputChange}
            required
            margin="normal"
            placeholder="Enter API key"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={handleRevealToggle} size="large">
                    {showApiKey ? <Visibility /> : <VisibilityOff />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </Grid>

        <Grid item xs={1}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Button
              variant="contained"
              color="primary"
              onClick={handleApiKeyChange}
              size="small"
            >
              Update
            </Button>
          </Box>
        </Grid>

        <Grid item xs={10}>
          {apiStatus.message && (
            <Alert severity={apiStatus.type} className="launcher-alert" sx={{ whiteSpace: "pre-line" }}>
              {apiStatus.message}
            </Alert>
          )}
        </Grid>
      </Grid>
    </>
  );
};