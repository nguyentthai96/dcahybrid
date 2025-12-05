import React from 'react';
import { Box, Typography } from '@mui/material';

interface Props {
    status: { merkle_root: string; total_certs: number };
}

const StatusBar: React.FC<Props> = ({ status }) => (
    <Box className="bg-blue-900 text-white p-4 rounded-lg text-sm"
         display="grid"
         // flexDirection="column"
         // alignItems="flex-start"
         gridTemplateColumns="1fr 1fr"
         gap={2}
         p="5px 50px"
    >
        <Typography>
            <strong>Merkle Root:</strong> {status.merkle_root ? status.merkle_root.substring(0, 20) + '...' : 'Empty'}
        </Typography>

        <Typography>
            <strong>Tổng Certs:</strong> {status.total_certs}   <a target="_blank" rel="noopener noreferrer" href="https://app.tryethernal.com/transactions">Tnx link</a>
        </Typography>
    </Box>
);

export default StatusBar;
