import './App.css'

import React, {useState, useEffect} from 'react';
import axios from 'axios';
import {Container, Box} from '@mui/material';
import VerifyForm from "./components/VerifyForm.tsx";
import SignForm from "./components/SignForm.tsx";
import Tabs from "./components/Tabs.tsx";
import StatusBar from "./components/StatusBar.tsx";
import Header from "./components/Header.tsx";
import type {CertificateDetails} from "./components/CertificateDetails.tsx";

interface SystemStatus {
    merkle_root: string;
    dca_certificate: string;
    total_certs: number;
}

const API_URL = "http://127.0.0.1:5000/api";
export {API_URL};

function App() {
    const [activeTab, setActiveTab] = useState<'sign' | 'verify'>('sign');
    const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
    const [parsedCertSysDetails, setParsedCertSysDetails] = React.useState<CertificateDetails>({} as CertificateDetails);

    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await axios.get(`${API_URL}/status`);
            setSystemStatus(res.data);
        } catch (error) {
            console.error("Backend offline ", error);
        }
    };


    return (
        <Box className="flex flex-col h-screen overflow-hidden bg-white">
            <Header />
            {systemStatus && <StatusBar status={systemStatus} setParsedCertSysDetails={setParsedCertSysDetails}/>}
            <Container maxWidth={false} className="flex flex-col h-full py-2 px-4">

                <Box className="mb-50 mt-20" marginBottom={2} marginTop={5}>
                     <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
                </Box>

                <Box className="flex-grow overflow-auto pb-3">
                    {activeTab === 'sign' ? (
                        <SignForm API_URL={API_URL} fetchStatus={fetchStatus} parsedCertSysDetails={parsedCertSysDetails} />
                    ) : (
                        <VerifyForm API_URL={API_URL} />
                    )}
                </Box>
            </Container>
        </Box>
    );
}

export default App;
