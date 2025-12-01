import { Typography, Box } from '@mui/material';

const Header = () => (
    <Box textAlign="center" className="mb-12">
        <Typography variant="h4" component="h1" className="text-blue-900 mb-1">
            Chứng thực số phi tập chung (Decentralized CA System)
        </Typography>
        <Typography variant="subtitle1" className="text-gray-700">
            MPC Threshold Signing & ZK-Transparency + Blockchain
        </Typography>
    </Box>
);

export default Header;