import { createTheme } from '@mui/material/styles';

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#ce93d8',
    },
    background: {
      default: '#0a1929',
      paper: '#0a1929',
    },
    success: {
      main: '#66bb6a',
    },
    error: {
      main: '#f44336',
    },
    warning: {
      main: '#ffa726',
    },
    info: {
      main: '#29b6f6',
    },
  },
  typography: {
    fontFamily: '"Roboto Mono", monospace',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#132f4c',
          borderRadius: 8,
        },
      },
    },
  },
});
