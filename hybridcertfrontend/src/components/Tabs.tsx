import React from 'react';
import { Button, Box } from '@mui/material';

interface Props {
    activeTab: 'sign' | 'verify';
    setActiveTab: (tab: 'sign' | 'verify') => void;
}

const Tabs: React.FC<Props> = ({ activeTab, setActiveTab }) => (
    <Box className="flex mb-6">
        <Button
            variant={activeTab === 'sign' ? 'contained' : 'outlined'}
            color="primary"
            className="flex-1 mr-2"
            onClick={() => setActiveTab('sign')}
        >
            Issue Certificate
        </Button>
        <Button
            variant={activeTab === 'verify' ? 'contained' : 'outlined'}
            color="primary"
            className="flex-1"
            onClick={() => setActiveTab('verify')}
        >
            Verify Document
        </Button>
    </Box>
);

export default Tabs;
