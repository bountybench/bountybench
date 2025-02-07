import { Button } from '@mui/material'
import ContentCopyIcon from "@mui/icons-material/ContentCopy";


export function CopyButton({ onClick }) {
	return (
		<Button variant='outlined' color='primaryDark' onClick={onClick} size='small' aria-label='copy' className='copy-button'>
			<ContentCopyIcon />
		</Button>
	);
}
