import React, {useState} from 'react';
import {Box, Button, Paper, TextField, Typography} from '@mui/material';
import axios from 'axios';

interface Props {
    API_URL: string;
}

const VerifyForm: React.FC<Props> = ({ API_URL }) => {
    const [verifyFile, setVerifyFile] = useState<File | null>(null);
    const [certJson, setCertJson] = useState('');
    const [verifyResult, setVerifyResult] = useState<any>(null);
    const [, setLoading] = useState(false);

    const handleVerify = async () => {
        if (!verifyFile || !certJson) return alert("Cần cung cấp CSR và Thông tin chứng chỉ JSON!");
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
                <Typography className="mb-1">2. Dán Thông tin Chứng chỉ JSON meta:</Typography>
                <TextField
                    fullWidth
                    multiline
                    placeholder='Dán JSON đã nhận được từ bước trước....'
                    value={certJson}
                    onChange={(e) => setCertJson(e.target.value)}
                    sx={{
                            "& .MuiInputBase-root": {
                                height: "50vh",
                                alignItems: "flex-start",
                                overflow: "auto",
                                borderTopLeftRadius: 0,
                                borderTopRightRadius: 0
                            }
                        }}
                        className="w-full shadow-inner border border-t-0 border-gray-300 rounded-b-md"
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
                        {verifyResult.valid ? "✅ Chứng chỉ hợp lệ (VALID DOCUMENT)" : "❌ Chứng chỉ không hợp lệ (INVALID DOCUMENT)"}
                    </Typography>
                    <Typography>{verifyResult.message}</Typography>
                </Paper>
            )}
        </Paper>
    );
};

export default VerifyForm;
