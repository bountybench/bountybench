import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import { Button } from '@mui/material'

export function KeyboardArrowRightButton({ color, onClick, ariaLabel, className, sx }) {
	return (
		<Button variant="outlined" color={color} onClick={onClick} size="small" aria-label={ariaLabel} className={className} sx={sx}>
      <KeyboardArrowRightIcon />
    </Button>
	);
}
