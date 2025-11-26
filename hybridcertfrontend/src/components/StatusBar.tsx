import React from 'react';
import { Box, Typography } from '@mui/material';

interface Props {
    status: { merkle_root: string; total_certs: number };
}

const StatusBar: React.FC<Props> = ({ status }) => (
    <Box className="bg-blue-900 text-white p-4 rounded-lg flex justify-around text-sm mb-6">
        {/*<Typography><strong>CA Nodes Active:</strong> 2/2 (A, B)</Typography>*/}
        <Typography>
            <strong>Merkle Root:</strong> {status.merkle_root ? status.merkle_root.substring(0, 20) + '...' : 'Empty'}
        </Typography>
        <Typography><strong>Tổng Certs:</strong> {status.total_certs}</Typography>
    </Box>
);

export default StatusBar;
