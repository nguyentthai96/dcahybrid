import React, {useState} from "react";
import {Alert, Box, Snackbar, TextField, Typography} from "@mui/material";


interface Props {
    dataJson: any;
}

const ResultJsonMetaCopyable: React.FC<Props> = ({dataJson}) => {
    const [openSnackbar, setOpenSnackbar] = useState(false); // Trạng thái thông báo copy

    // Hàm xử lý copy vào clipboard
    const handleCopy = () => {
        if (dataJson) {
            navigator.clipboard.writeText(JSON.stringify(dataJson, null, 2));
            setOpenSnackbar(true);
        }
    };

    return (
        <>
            {/* Kết quả hiển thị */}
            <Box className="flex flex-col flex-grow mt-2 text-left w-full">
                {/* Header kết quả */}
                <Box className="p-3 bg-green-50 border border-green-200 rounded-t-md mb-0">
                    <Typography variant="h6" className="text-green-800 font-bold flex items-center gap-2">
                        ✅ Cấp phát thành công (Certificate Issued)!
                    </Typography>

                    {/* Thông tin Hash & Signature: Căn trái */}
                    <div className="mt-2 text-sm text-gray-800 space-y-1">
                        <div style={{display: "flex", alignItems: "left"}}>
                            <strong className="mr-2">Cert Hash: </strong>
                            <span className="font-mono">{dataJson.certificate_hash}</span>
                        </div>
                        <div style={{display: "flex", alignItems: "left"}}>
                            <strong className="mr-2">Signature: </strong>
                            <span className="font-mono">{dataJson.signature.substring(0, 50)}...</span>
                        </div>
                        <div style={{display: "flex", alignItems: "left"}}>
                            <strong className="mr-2">Tổng thời gian ký: </strong>
                            <span className="font-mono">{dataJson['timing'].total_ms} millisecond</span>
                        </div>
                    </div>
                </Box>

                {/* TextField JSON Full Màn Hình */}
                {/* Dòng chữ Click để Copy */}
                <Typography
                    variant="caption"
                    className="mt-2 text-blue-600 cursor-pointer hover:underline text-center block w-full py-2 bg-blue-50 rounded border border-blue-100 font-semibold"
                    onClick={handleCopy}
                >
                    📋 Sao chép JSON meta lưu trữ
                </Typography>
                <TextField
                    fullWidth
                    multiline
                    // Bỏ rows cố định, dùng CSS để ép chiều cao
                    value={JSON.stringify(dataJson, null, 2)}
                    slotProps={{
                        input: {
                            //readOnly: true,
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
            </Box>

            <Snackbar
                open={openSnackbar}
                autoHideDuration={3000}
                onClose={() => setOpenSnackbar(false)}
                anchorOrigin={{vertical: 'bottom', horizontal: 'center'}}
            >
                <Alert severity="success" variant="filled">
                    Đã sao chép JSON vào bộ nhớ tạm!
                </Alert>
            </Snackbar>
        </>
    );
};

export default ResultJsonMetaCopyable;