import React, {useState} from 'react';
import {Box, Button, Paper, TextField, Typography} from '@mui/material';
import axios from 'axios';
import {IssueCertificate} from "./IssueCertificate.tsx";
import {CertificateDetails} from "./CertificateDetails.tsx";
import ResultJsonMetaCopyable from "./ResultJsonMetaCopyable.tsx";

interface Props {
    API_URL: string;
    fetchStatus: () => void;
    parsedCertSysDetails: CertificateDetails;
}

const SignForm: React.FC<Props> = ({API_URL, fetchStatus, parsedCertSysDetails}) => {
    // const [signFile, setSignFile] = useState<File | null>(null);
    // const [metadata, setMetadata] = useState<string>();
    // const [signResult, setSignResult] = useState<any>(null);
    //
    // const handleSign = async () => {
    //     if (!signFile) return alert("Vui lòng chọn file tài liệu!");
    //     const formData = new FormData();
    //     formData.append('file', signFile);
    //     formData.append('metadata', metadata || "No description");
    //
    //     try {
    //         const res = await axios.post(`${API_URL}/sign`, formData);
    //         setSignResult(res.data);
    //         fetchStatus();
    //     } catch (err) {
    //         alert("Ký số thất bại (Signing failed)");
    //     }
    // };

    return (
        <Paper elevation={0} className="h-full flex flex-col p-4 shadow-none border-0">
            <IssueCertificate parsedCertSysDetails={parsedCertSysDetails} fetchStatus={fetchStatus}/>
            {/*<Box className="flex flex-row items-center gap-4 mb-4">*/}
            {/*    <Typography className="font-bold text-gray-700 whitespace-nowrap min-w-fit">*/}
            {/*        1. Upload Tài liệu gốc:*/}
            {/*    </Typography>*/}
            {/*    <input*/}
            {/*        type="file"*/}
            {/*        className="text-sm cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"*/}
            {/*        onChange={(e) => setSignFile(e.target.files?.[0] || null)}*/}
            {/*    />*/}
            {/*</Box>*/}

            {/*/!* 2. Metadata: Căn trái *!/*/}
            {/*<Box className="mb-4 text-left">*/}
            {/*    <Typography className="font-bold text-gray-700 mb-1">*/}
            {/*        2. Dữ liệu đặc tả (Metadata - Tên sở hữu, ID...):*/}
            {/*    </Typography>*/}
            {/*    <TextField*/}
            {/*        fullWidth*/}
            {/*        size="small"*/}
            {/*        variant="outlined"*/}
            {/*        placeholder="Ví dụ: Alice - ID 12345"*/}
            {/*        value={metadata}*/}
            {/*        onChange={(e) => setMetadata(e.target.value)}*/}
            {/*    />*/}
            {/*</Box>*/}

            {/*/!* Nút Ký *!/*/}
            {/*<Button*/}
            {/*    variant="contained"*/}
            {/*    color="success"*/}
            {/*    fullWidth*/}
            {/*    size="large"*/}
            {/*    onClick={handleSign}*/}
            {/*    className="mb-6 font-bold"*/}
            {/*>*/}
            {/*    KÝ CHỨNG CHỈ SỐ (Digital Certificate Signing)*/}
            {/*</Button>*/}

            {/*/!* Kết quả hiển thị *!/*/}
            {/*{signResult && (*/}
            {/*    <ResultJsonMetaCopyable dataJson={signResult}/>*/}
            {/*)}*/}
        </Paper>
    );
};

export default SignForm;