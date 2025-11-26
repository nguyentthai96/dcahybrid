import React, { useState } from 'react';
import { Box, Typography, TextField, Button, Paper } from '@mui/material';
import axios from 'axios';

interface Props {
    API_URL: string;
    fetchStatus: () => void;
}

const SignForm: React.FC<Props> = ({ API_URL, fetchStatus }) => {
    const [signFile, setSignFile] = useState<File | null>(null);
    const [metadata, setMetadata] = useState();
    const [signResult, setSignResult] = useState<any>(null);

    const handleSign = async () => {
        if (!signFile) return alert("Please select a file!");
        const formData = new FormData();
        formData.append('file', signFile);
        formData.append('metadata', metadata || "No description");

        try {
            const res = await axios.post(`${API_URL}/sign`, formData);
            setSignResult(res.data);
            fetchStatus();
        } catch (err) {
            alert("Signing failed");
        }
    };

    return (
        <Paper className="p-6 shadow rounded-lg">
            <Box >
                <Typography className="mb-1">1. Upload Tài liệu:</Typography>
                <input type="file" onChange={(e) => setSignFile(e.target.files?.[0] || null)} />
            </Box>

            <Box >
                <Typography className="mb-1">2. Metadata (Tên sở hữu, ID...):</Typography>
                <TextField
                    fullWidth
                    variant="outlined"
                    placeholder="e.g. Alice - ID 12345"
                    value={metadata}
                    onChange={(e) => setMetadata(e.target.value)}
                />
            </Box>

            <Button variant="contained" color="success" fullWidth onClick={handleSign}>
                Ký chứng chỉ
            </Button>

            {signResult && (
                <Paper className="p-4 mt-6 bg-green-100 border border-green-300 text-green-900 break-words">
                    <Typography variant="h6">✅ Certificate Issued!</Typography>
                    <Typography><strong>Cert Hash:</strong> {signResult.certificate_hash}</Typography>
                    <Typography><strong>Signature (r):</strong> {signResult.signature.r.substring(0,20)}...</Typography>
                    <TextField
                        fullWidth
                        multiline
                        rows={8}
                        value={JSON.stringify(signResult, null, 2)}
                        InputProps={{ readOnly: true }}
                        className="mt-2"
                    />
                    <Typography variant="caption">Copy the JSON above to Verify later.</Typography>
                </Paper>
            )}
        </Paper>
    );
};

export default SignForm;
