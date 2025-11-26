import './App.css'

import {useState, useEffect} from 'react';
import axios from 'axios';
import {Container} from '@mui/material';
import VerifyForm from "./components/VerifyForm.tsx";
import SignForm from "./components/SignForm.tsx";
import Tabs from "./components/Tabs.tsx";
import StatusBar from "./components/StatusBar.tsx";
import Header from "./components/Header.tsx";

interface SystemStatus {
    merkle_root: string;
    total_certs: number;
}

const API_URL = "http://127.0.0.1:5000/api";

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
            console.error("Backend offline");
        }
    };


    return (
        <>
            <Header/>
            {systemStatus && <StatusBar status={systemStatus}/>}
            <Tabs activeTab={activeTab} setActiveTab={setActiveTab}/>
            <div className="mt-6">
                {activeTab === 'sign' ? (
                    <SignForm API_URL={API_URL} fetchStatus={fetchStatus}/>
                ) : (
                    <VerifyForm API_URL={API_URL}/>
                )}
            </div>
        </>
    );
}

export default App;
