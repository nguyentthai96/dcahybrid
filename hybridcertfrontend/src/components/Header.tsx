import { Typography, Box } from '@mui/material';

const Header = () => (
    <Box textAlign="center" className="mb-6">
        <Typography variant="h4" component="h1" className="text-blue-900 mb-1">
            Decentralized CA System
        </Typography>
        <Typography variant="subtitle1" className="text-gray-700">
            MPC Threshold Signing & ZK-Transparency
        </Typography>
    </Box>
);

export default Header;