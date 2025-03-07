import { Box } from '@mui/material';
import { CopyButton } from './CopyButton';
import { EditButton } from './EditButton';
import { CloseButton } from './CloseButton';
import { KeyboardArrowRightButton } from './KeyboardArrowRightButton';

export function RunButtonBoxComponent({ handleCopyClick, handleEditClick, handleRunClick }) {
	return (
		<Box className="message-buttons" sx={{ display: 'flex' }}>
  			<CopyButton onClick={handleCopyClick} />
			<EditButton onClick={handleEditClick} />
           		<KeyboardArrowRightButton onClick={handleRunClick} color="secondary" ariaLabel="run" className="run-button" />
    	</Box>
	);
}

export function SaveButtonBoxComponent({ handleCopyClick, handleCancelEdit, handleSaveClick }) {
	return (
		<Box className="message-buttons" sx={{ display: 'flex' }}>
  			<CopyButton onClick={handleCopyClick} />
			<CloseButton onClick={handleCancelEdit}/>
            		<KeyboardArrowRightButton onClick={handleSaveClick} color="primary" ariaLabel="save" className="save-button" sx={{mr: 1}}/>
    	</Box>
	);
}

