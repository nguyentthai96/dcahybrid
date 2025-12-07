import React, {useRef, useState} from "react";
import {Box, TextField, Typography} from "@mui/material";
import {CloudUpload} from "@mui/icons-material";

const FileUploadBox = ({ label, file, setFile, textContent, setTextContent, icon, accept }: any) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragOver, setIsDragOver] = useState(false);

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            setFile(droppedFile);
            if (setTextContent) setTextContent(await droppedFile.text());
        }
    };

    return (
        <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                {icon} {label}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "row", gap: 2 }}>
                <Box flex={1}
                     onDrop={handleDrop}
                     onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                     onDragLeave={() => setIsDragOver(false)}
                     onClick={() => fileInputRef.current?.click()}
                     sx={{
                         border: isDragOver ? "2px dashed #1976d2" : "2px dashed #ccc",
                         borderRadius: 2, p: 2,
                         display: "flex", flexDirection: "column",
                         alignItems: "center", justifyContent: "center",
                         minHeight: "100px", cursor: "pointer",
                         bgcolor: isDragOver ? "#f0f7ff" : "#fafafa",
                         transition: "all 0.2s"
                     }}
                >
                    <CloudUpload sx={{ color: isDragOver ? "#1976d2" : "gray", mb: 1 }} />
                    <Typography variant="body2" align="center" color="textSecondary">
                        {!file ? "Click or Drag file" : file.name}
                    </Typography>
                    <input
                        type="file"
                        accept={accept}
                        ref={fileInputRef}
                        style={{ display: "none" }}
                        onChange={async (e) => {
                            const f = e.target.files?.[0];
                            if (f) {
                                setFile(f);
                                if (setTextContent) setTextContent(await f.text());
                            }
                        }}
                    />
                </Box>
                {setTextContent && (
                    <Box flex={2}>
                        <TextField
                            multiline fullWidth rows={4}
                            value={textContent}
                            placeholder="File content preview..."
                            slotProps={{
                                input: {
                                    readOnly: true,
                                    style: { fontFamily: "Monaco, monospace", fontSize: "11px", backgroundColor: "#f5f5f5" },
                                }
                            }}
                        />
                    </Box>
                )}
            </Box>
        </Box>
    );
};

export default FileUploadBox;