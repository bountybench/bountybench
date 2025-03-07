import { IconButton } from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

export function ToggleExpandButton({expanded, className,,ariaLabel}) {
	return (
		<IconButton 
			onClick={handleExpandClick}
            aria-expanded={expanded}
            aria-label={ariaLabel}
            className={className}
          >
        	{expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
    	</IconButton>
	);
}
