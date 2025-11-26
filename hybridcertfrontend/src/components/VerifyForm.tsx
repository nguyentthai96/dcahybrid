import React, { useState } from 'react';
import { Box, Typography, TextField, Button, Paper, Grid, Alert } from '@mui/material';
import axios from 'axios';

interface Props {
    API_URL: string;
}

const VerifyForm: React.FC<Props> = ({ API_URL }) => {
    const [verifyFile, setVerifyFile] = useState<File | null>(null);
    const [certJson, setCertJson] = useState('');
    const [verifyResult, setVerifyResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const handleVerify = async () => {
        if (!verifyFile || !certJson) return alert("Please select file AND paste certificate JSON!");
        setLoading(true);
        const formData = new FormData();
        formData.append('file', verifyFile);
        formData.append('certificate', certJson);

        try {
            const res = await axios.post(`${API_URL}/verify`, formData);
            setVerifyResult(res.data);
        } catch (err) {
            setVerifyResult({ valid: false, message: "Server Error or Invalid Format" });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Paper className="p-6 shadow rounded-lg">
            <Box>
                <Typography className="mb-1">1. Upload Tài liệu:</Typography>
                <input type="file" onChange={(e) => setVerifyFile(e.target.files?.[0] || null)} />
            </Box>

            <Box >
                <Typography className="mb-1">2. Paste Certificate JSON:</Typography>
                <TextField
                    fullWidth
                    multiline
                    rows={5}
                    placeholder='Dán JSON đã nhận được từ bước cấp phát chứng chỉ ‘Issue’....'
                    value={certJson}
                    onChange={(e) => setCertJson(e.target.value)}
                />
            </Box>

            <Button variant="contained" color="primary" fullWidth onClick={handleVerify}>
                Xác thực chứng chỉ
            </Button>

            {verifyResult && (
                <Paper className={`p-4 mt-6 border rounded break-words ${
                    verifyResult.valid ? 'bg-green-100 border-green-300 text-green-900' : 'bg-red-100 border-red-300 text-red-900'
                }`}>
                    <Typography variant="h6">
                        {verifyResult.valid ? "✅ VALID DOCUMENT" : "❌ INVALID DOCUMENT"}
                    </Typography>
                    <Typography>{verifyResult.message}</Typography>
                </Paper>
            )}
        </Paper>
    );
};

export default VerifyForm;
