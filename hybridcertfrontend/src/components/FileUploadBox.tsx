import React, { useRef, useState } from 'react';
import { Box, Typography, TextField, Paper } from '@mui/material';

interface FileUploadBoxProps {
    label: string;
    file: File | null;
    setFile: (f: File | null) => void;
    textContent: string;
    setTextContent: (s: string) => void;
    icon: React.ReactNode;
    accept: string;
}

export default function FileUploadBox({ label, file, setFile, textContent, setTextContent, icon, accept }: FileUploadBoxProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragOver, setIsDragOver] = useState(false);

    const handleFileChange = (uploadedFile: File | null) => {
        if (!uploadedFile) return;
        setFile(uploadedFile);

        const reader = new FileReader();
        reader.onload = (e) => {
            if (e.target?.result && typeof e.target.result === 'string') {
                setTextContent(e.target.result);
            }
        };
        reader.readAsText(uploadedFile);
    };

    return (
        <Paper variant="outlined" sx={{ p: 2, mb: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold' }}>
                {icon} {label}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "row", gap: 2 }}>
                <Box flex={1}
                     onDrop={(e) => {
                         e.preventDefault(); setIsDragOver(false);
                         handleFileChange(e.dataTransfer.files?.[0]);
                     }}
                     onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                     onDragLeave={() => setIsDragOver(false)}
                     onClick={() => fileInputRef.current?.click()}
                     sx={{
                         border: isDragOver ? "2px dashed #1976d2" : "2px dashed #ccc",
                         bgcolor: isDragOver ? "#f0f7ff" : "transparent",
                         padding: 2, display: "flex", flexDirection: "column",
                         alignItems: "center", justifyContent: "center",
                         minHeight: "100px", cursor: "pointer", borderRadius: 1
                     }}
                >
                    <Typography variant="body2" align="center" color="textSecondary">
                        {file ? file.name : "Click or Drop File Here"}
                    </Typography>
                    <input
                        type="file" ref={fileInputRef} style={{ display: "none" }}
                        accept={accept}
                        onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                    />
                </Box>
                <Box flex={2}>
                    <TextField
                        multiline rows={4} fullWidth
                        value={textContent}
                        placeholder="PEM content will appear here..."
                        onChange={(e) => setTextContent(e.target.value)}
                        slotProps={{
                            input: {
                                style: { fontFamily: "Monospace", fontSize: "12px" },
                            }
                        }}
                    />
                </Box>
            </Box>
        </Paper>
    );
}