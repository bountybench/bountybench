import CloseIcon from '@mui/icons-material/Close';
import { Button } from '@mui/material'

export function CloseButton({ onClick }) {
	return (
		<Button variant="outlined" color="secondary" onClick={onClick} size="small" aria-label="cancel" className="cancel-button">
      <CloseIcon/>
    </Button>
	);
}
