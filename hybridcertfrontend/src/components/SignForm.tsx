import React, {useState} from 'react';
import {Alert, Box, Button, Paper, Snackbar, TextField, Typography} from '@mui/material';
import axios from 'axios';

interface Props {
    API_URL: string;
    fetchStatus: () => void;
}

const SignForm: React.FC<Props> = ({ API_URL, fetchStatus }) => {
    const [signFile, setSignFile] = useState<File | null>(null);
    const [metadata, setMetadata] = useState<string>();
    const [signResult, setSignResult] = useState<any>(null);
    const [openSnackbar, setOpenSnackbar] = useState(false); // Trạng thái thông báo copy

    const handleSign = async () => {
        if (!signFile) return alert("Vui lòng chọn file tài liệu!");
        const formData = new FormData();
        formData.append('file', signFile);
        formData.append('metadata', metadata || "No description");

        try {
            const res = await axios.post(`${API_URL}/sign`, formData);
            setSignResult(res.data);
            fetchStatus();
        } catch (err) {
            alert("Ký số thất bại (Signing failed)");
        }
    };

    // Hàm xử lý copy vào clipboard
    const handleCopy = () => {
        if (signResult) {
            navigator.clipboard.writeText(JSON.stringify(signResult, null, 2));
            setOpenSnackbar(true);
        }
    };

    return (
        <Paper elevation={0} className="h-full flex flex-col p-4 shadow-none border-0">
            <Box className="flex flex-row items-center gap-4 mb-4">
                <Typography className="font-bold text-gray-700 whitespace-nowrap min-w-fit">
                    1. Upload Tài liệu gốc:
                </Typography>
                <input
                    type="file"
                    className="text-sm cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    onChange={(e) => setSignFile(e.target.files?.[0] || null)}
                />
            </Box>

            {/* 2. Metadata: Căn trái */}
            <Box className="mb-4 text-left">
                <Typography className="font-bold text-gray-700 mb-1">
                    2. Dữ liệu đặc tả (Metadata - Tên sở hữu, ID...):
                </Typography>
                <TextField
                    fullWidth
                    size="small"
                    variant="outlined"
                    placeholder="Ví dụ: Alice - ID 12345"
                    value={metadata}
                    onChange={(e) => setMetadata(e.target.value)}
                />
            </Box>

            {/* Nút Ký */}
            <Button
                variant="contained"
                color="success"
                fullWidth
                size="large"
                onClick={handleSign}
                className="mb-6 font-bold"
            >
                KÝ CHỨNG CHỈ SỐ (Digital Certificate Signing)
            </Button>

            {/* Kết quả hiển thị */}
            {signResult && (
                <Box className="flex flex-col flex-grow mt-2 text-left w-full">
                    {/* Header kết quả */}
                    <Box className="p-3 bg-green-50 border border-green-200 rounded-t-md mb-0">
                        <Typography variant="h6" className="text-green-800 font-bold flex items-center gap-2">
                            ✅ Ký thành công (Certificate Issued)!
                        </Typography>

                        {/* Thông tin Hash & Signature: Căn trái */}
                        <div className="mt-2 text-sm text-gray-800 space-y-1">
                            <div>
                                <strong className="mr-2">Cert Hash: </strong>
                                <span className="font-mono">{signResult.certificate_hash}</span>
                            </div>
                            <div>
                                <strong className="mr-2">Signature (r): </strong>
                                <span className="font-mono">{signResult.signature.r.substring(0, 50)}...</span>
                            </div>
                            <div>
                                <strong className="mr-2">Tổng thời gian ký: </strong>
                                <span className="font-mono">{signResult.timing.total_ms} millisecond</span>
                            </div>
                        </div>
                    </Box>

                    {/* TextField JSON Full Màn Hình */}
                    <TextField
                        fullWidth
                        multiline
                        // Bỏ rows cố định, dùng CSS để ép chiều cao
                        value={JSON.stringify(signResult, null, 2)}
                        slotProps={{
                            input: {
                                readOnly: true,
                                className: "font-mono text-sm bg-gray-50",
                            }
                        }}
                        sx={{
                            "& .MuiInputBase-root": {
                                height: "50vh",
                                alignItems: "flex-start", // Text bắt đầu từ trên cùng
                                overflow: "auto",
                                borderTopLeftRadius: 0,
                                borderTopRightRadius: 0
                            }
                        }}
                        className="w-full shadow-inner rounded-b-md"
                    />

                    {/* Dòng chữ Click để Copy */}
                    <Typography
                        variant="caption"
                        className="mt-2 text-blue-600 cursor-pointer hover:underline text-center block w-full py-2 bg-blue-50 rounded border border-blue-100 font-semibold"
                        onClick={handleCopy}
                    >
                        📋 Sao chép JSON meta cho bước Xác thực
                    </Typography>
                </Box>
            )}

            <Snackbar
                open={openSnackbar}
                autoHideDuration={3000}
                onClose={() => setOpenSnackbar(false)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert severity="success" variant="filled">
                    Đã sao chép JSON vào bộ nhớ tạm!
                </Alert>
            </Snackbar>
        </Paper>
    );
};

export default SignForm;