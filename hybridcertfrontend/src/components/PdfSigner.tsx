import {useState} from 'react';
import {Alert, Box, Button, Container, Divider, Paper, Typography} from '@mui/material';
import {CheckCircle, Download, Error as ErrorIcon, PictureAsPdf, VerifiedUser, VpnKey} from '@mui/icons-material';
import {signPdfPAdES} from '../pdfSigning';
import {verifyPdfPAdES, type VerifyResult,} from '../pdfVerification';
import FileUploadBox from "./FileUploadBox.tsx";

export interface CaStatusSystemInfo {
    merkle_root: string;
    total_certs: number;
    dca_certificate: string;
}

interface PdfSignerProps {
    caSystemInfo: CaStatusSystemInfo | null;
}

export default function PdfSigner({caSystemInfo}: PdfSignerProps) {
    const [keyFile, setKeyFile] = useState<string>("");
    const [certFile, setCertFile] = useState<string>("");
    // const [caFile, setCaFile] = useState<string>("");
    //
    const [pdfFile, setPdfFile] = useState<File | null>(null);
    //
    const [signedUrl, setSignedUrl] = useState<string | null>(null);
    const [signError, setSignError] = useState<string | null>(null);
    //
    const [verifyFile, setVerifyFile] = useState<File | null>(null);
    const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
    //

    /*const readFile = (file: File) => new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsText(file);
    });*/

    const handleSign = async (pdfFile: File) => {
        setPdfFile(pdfFile);
        if (!keyFile || !certFile || !pdfFile) return setSignError("Missing Private Key, User Cert or PDF");
        try {
            const pdfBuffer = await pdfFile.arrayBuffer();
            const signedBytes = await signPdfPAdES(pdfBuffer, keyFile, certFile, caSystemInfo?.dca_certificate);
            const blob = new Blob([signedBytes as any], {type: "application/pdf"});
            setSignedUrl(URL.createObjectURL(blob));
            setSignError(null);
        } catch (e: any) {
            console.error("PdfSigner Error: ", e.message || e || "Unknown Error")
            setSignError(e.message);
            setSignedUrl(null);
        }
    };

    const handleVerify = async (file:File) => {
        if (!file) return;
        const buffer = await file.arrayBuffer();
        const res = await verifyPdfPAdES(buffer);
        setVerifyResult(res);
    };

    return (
        <Container maxWidth="lg">
            <Paper sx={{p: 3}}>
                <Typography variant="h6" gutterBottom color="primary">PAdES-B ECDSA Signer</Typography>
                {/* PRIVATE KEY */}
                <FileUploadBox
                    label="Private Key"
                    icon={<VpnKey/>}
                    accept=".pem,.key,.txt"
                    externalText={keyFile}
                    onDataChange={(file: File, text) => {
                        setKeyFile(text.trim());
                    }}
                />
                {/* USER CERT */}
                <FileUploadBox
                    label="User Certificate"
                    icon={<VerifiedUser/>}
                    accept=".pem,.crt,.cer,.txt"
                    externalText={certFile}
                    onDataChange={(file, text) => {
                        setCertFile(text.trim());
                    }}
                />

                {/* PDF */}
                <Button component="label" variant="contained" startIcon={<PictureAsPdf/>} fullWidth
                        sx={{mb: 2, height: 50}}>
                    {pdfFile ? ((pdfFile.name) + (signedUrl ? " (Signed)" : "")) : "Select PDF"}
                    <input type="file" hidden accept="application/pdf"
                           onChange={(e) => {
                               handleSign(e.target.files?.[0] as File || null );
                           }}/>
                </Button>

                <Divider sx={{my: 2}}/>

                {signError && (<Alert severity="error" sx={{mb: 2}}>{signError}</Alert>)}
                {signedUrl && !signError && (
                    <Box mx="auto" sx={{height: 800, bgcolor: '#525659', borderRadius: 2,}}>
                        {signedUrl ? <iframe src={signedUrl} width="100%" height="100%"/> : null}
                    </Box>)}
                {signedUrl && <Button href={signedUrl} download={pdfFile?.name + "signed.pdf"} startIcon={<Download/>}
                                      sx={{mt: 2}}>Download</Button>}

                <Divider sx={{my: 3}}/>
                <Divider sx={{my: 2}}/>
            </Paper>
            <Paper sx={{p: 3}}>
                {/* <!-- VERIFY PDF --> */}
                <Typography variant="h6" gutterBottom color="primary">Verify PAdES-B ECDSA Signed</Typography>
                <Box mx="auto">
                    <Button component="label" variant="outlined" fullWidth sx={{height: 100, borderStyle: 'dashed'}}>
                        {verifyFile ? verifyFile.name : "Upload PDF to Verify"}
                        <input type="file" hidden accept="application/pdf"
                               onChange={(e) => {
                                   setVerifyFile(e.target.files?.[0] || null);
                                   handleVerify(e.target.files?.[0] || null);
                               }
                        }/>
                    </Button>
                    {verifyResult && (
                        <Paper sx={{mt: 3, p: 2, bgcolor: verifyResult.isValid ? '#e8f5e9' : '#ffebee'}}>
                            <Box display="flex" alignItems="center" justifyContent={"center"} gap={1} mb={2}>
                                {verifyResult.isValid ? <CheckCircle color="success"/> : <ErrorIcon color="error"/>}
                                <Typography variant="h5" align={"center"}>{verifyResult.isValid ? "VALID" : "INVALID"}</Typography>
                            </Box>
                            <Typography align={"left"}><strong>Subject:</strong> {verifyResult.signerSubject}</Typography>
                            <Typography align={"left"}><strong>Issuer:</strong> {verifyResult.signerIssuer}</Typography>
                            <Typography  align={"left"}><strong>Time:</strong> {verifyResult.signingTime?.toLocaleString()}</Typography>
                            {verifyResult.errors.map((e, i) => <Alert severity="error" key={i}
                                                                      sx={{mt: 1}}>{e}</Alert>)}
                        </Paper>
                    )}
                </Box>
            </Paper>
        </Container>
    );
}