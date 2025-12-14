import './App.css'

import {useEffect, useState} from 'react';
import axios from 'axios';
import {Box, Container} from '@mui/material';
import Tabs from "./components/Tabs.tsx";
import StatusBar from "./components/StatusBar.tsx";
import Header from "./components/Header.tsx";
import {IssueCertificate} from "./components/IssueCertificate.tsx";
import PdfSigner from "./components/PdfSigner.tsx";

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
            <Header/>
            {systemStatus && <StatusBar status={systemStatus}/>}
            <Container maxWidth={false} className="flex flex-col h-full py-2 px-4">

                <Box className="mb-50 mt-20" marginBottom={2} marginTop={5}>
                    <Tabs activeTab={activeTab} setActiveTab={setActiveTab}/>
                </Box>

                <Box className="flex-grow overflow-auto pb-3">
                    {activeTab === 'sign' ? (
                        <IssueCertificate fetchStatus={fetchStatus}/>
                    ) : (
                        <PdfSigner caSystemInfo={systemStatus}/>
                    )}
                </Box>
            </Container>
        </Box>
    );
}

export default App;
