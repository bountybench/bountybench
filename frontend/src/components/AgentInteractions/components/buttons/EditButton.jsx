import EditIcon from '@mui/icons-material/Edit';
import { Button } from '@mui/material'

export function EditButton({ onClick }) {
	return (
		<Button variant="outlined" color="primary" onClick={onClick} size="small" aria-label="edit" className="edit-button">
        <EditIcon />
    </Button>
	);
}
