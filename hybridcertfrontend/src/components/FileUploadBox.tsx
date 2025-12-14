import React, {useEffect, useRef, useState} from 'react';
import {Box, Paper, TextField, Typography} from '@mui/material';

interface FileUploadBoxProps {
    label: string;
    icon: React.ReactNode;
    accept: string;
    onDataChange: (file: File | null, text: string) => void;
    externalText?: string;
}

export default function FileUploadBox({
                                          label, icon, accept,
                                          onDataChange, externalText
                                      }: FileUploadBoxProps) {

    const fileInputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [textContent, setTextContent] = useState("");
    //
    const [isDragOver, setIsDragOver] = useState(false);

    // Sync từ parent → child nếu externalText thay đổi
    useEffect(() => {
        if (externalText !== undefined) {
            setTextContent(externalText);
        }
    }, [externalText]);

    const handleFileChange = (uploadedFile: File | null) => {
        if (!uploadedFile) return;
        setFile(uploadedFile);


        const reader = new FileReader();
        reader.onload = (e) => {
            const text = typeof e.target?.result === "string" ? e.target.result : "";
            setTextContent(text);
            onDataChange(uploadedFile, text);  // forward ra parent
        };
        reader.readAsText(uploadedFile);
    };

    return (
        <Paper variant="outlined" sx={{p: 2, display: "flex", flexDirection: "column", gap: 2}}>
            <Box sx={{display: "flex", flexDirection: "row", gap: 2}}>
                <Box flex={1.25}
                     onClick={() => fileInputRef.current?.click()}
                     onDragOver={(e) => {
                         e.preventDefault();
                         setIsDragOver(true);
                     }}
                     onDragLeave={() => setIsDragOver(false)}
                     onDragEnter={() => setIsDragOver(false)}
                     onDrop={(e) => {
                         e.preventDefault();
                         setIsDragOver(false);
                         handleFileChange(e.dataTransfer.files?.[0]);
                     }}
                     sx={{
                         border: isDragOver ? "2px dashed #1976d2" : "2px dashed #ccc",
                         bgcolor: isDragOver ? "#f0f7ff" : "transparent",
                         padding: 2,
                         display: "flex", flexDirection: "column",
                         alignItems: "center", justifyContent: "center",
                         minHeight: "100px", cursor: "pointer", borderRadius: 1
                     }}
                >
                    <Typography variant="subtitle2" sx={{display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold'}}>
                        {icon} {label}
                    </Typography>
                    <Typography variant="body2" align="center" color="textSecondary">
                        {file ? file.name : "Nhấp hoặc kéo thả tệp vào đây"}
                    </Typography>
                    <input
                        type="file" style={{display: "none"}}
                        accept={accept}
                        hidden
                        ref={fileInputRef}
                        onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                    />
                </Box>

                {/* Text Content Area */}
                <Box sx={{display: 'inline-flex'}} flex={5}>
                    <TextField
                        fullWidth
                        multiline
                        rows={10}
                        placeholder="Nội dung dự liệu sẽ hiển thị tại đây..."
                        value={textContent}
                        onChange={(e) => setTextContent(e.target.value)}
                        slotProps={{
                            input: {
                                readOnly: true,
                                style: {
                                    fontFamily: "monospace",
                                    fontSize: "12px"
                                }
                            }
                        }}
                    />
                </Box>
            </Box>
        </Paper>
    );
}