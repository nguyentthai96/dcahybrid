import  {useState} from 'react';
import {Alert, Box, Button, Container, Divider, Grid, Paper, Tab, Tabs, TextField, Typography} from '@mui/material';
import {CheckCircle, Download, Error as ErrorIcon, PictureAsPdf, VerifiedUser, VpnKey} from '@mui/icons-material';
import {signPdfPAdES} from '../pdfSigning';
import {verifyPdfPAdES, type VerifyResult,} from '../pdfVerification';

export default function PdfSigner() {
    const [tab, setTab] = useState(0);
    const [keyFile, setKeyFile] = useState<string>("");
    const [certFile, setCertFile] = useState<string>("");
    const [caFile, setCaFile] = useState<string>("");
    const [pdfFile, setPdfFile] = useState<File | null>(null);
    const [signedUrl, setSignedUrl] = useState<string | null>(null);
    const [signError, setSignError] = useState<string | null>(null);
    const [verifyFile, setVerifyFile] = useState<File | null>(null);
    const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);

    const readFile = (file: File) => new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsText(file);
    });

    const handleSign = async () => {
        if (!keyFile || !certFile || !pdfFile) return setSignError("Missing Private Key, User Cert or PDF");
        try {
            const pdfBuffer = await pdfFile.arrayBuffer();
            const signedBytes = await signPdfPAdES(pdfBuffer, keyFile, certFile, caFile || undefined);
            const blob = new Blob([signedBytes as any], { type: "application/pdf" });
            setSignedUrl(URL.createObjectURL(blob));
            setSignError(null);
        } catch (e: any) {
            setSignError(e.message);
        }
    };

    const handleVerify = async () => {
        if (!verifyFile) return;
        const buffer = await verifyFile.arrayBuffer();
        const res = await verifyPdfPAdES(buffer);
        setVerifyResult(res);
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h5" gutterBottom color="primary">PAdES-B ECDSA Signer</Typography>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
                    <Tab label="Sign" />
                    <Tab label="Verify" />
                </Tabs>

                {tab === 0 ? (
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={5}>
                            <Button component="label" variant="outlined" startIcon={<VpnKey />} fullWidth sx={{ mb: 1 }}>
                                Upload Private Key
                                <input type="file" hidden onChange={async (e) => e.target.files?.[0] && setKeyFile(await readFile(e.target.files[0]))} />
                            </Button>
                            <TextField size="small" fullWidth value={keyFile ? "Key Loaded" : ""} disabled sx={{mb: 2}}/>

                            <Button component="label" variant="outlined" startIcon={<VerifiedUser />} fullWidth sx={{ mb: 1 }}>
                                Upload User Cert
                                <input type="file" hidden onChange={async (e) => e.target.files?.[0] && setCertFile(await readFile(e.target.files[0]))} />
                            </Button>
                            <TextField size="small" fullWidth value={certFile ? "Cert Loaded" : ""} disabled sx={{mb: 2}}/>

                            <Button component="label" variant="outlined" startIcon={<VerifiedUser />} fullWidth sx={{ mb: 1 }}>
                                Upload CA Chain (Optional)
                                <input type="file" hidden onChange={async (e) => e.target.files?.[0] && setCaFile(await readFile(e.target.files[0]))} />
                            </Button>

                            <Divider sx={{ my: 2 }} />

                            <Button component="label" variant="contained" startIcon={<PictureAsPdf />} fullWidth sx={{ mb: 2, height: 50 }}>
                                {pdfFile ? pdfFile.name : "Select PDF"}
                                <input type="file" hidden accept="application/pdf" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} />
                            </Button>

                            {signError && <Alert severity="error" sx={{ mb: 2 }}>{signError}</Alert>}
                            <Button variant="contained" color="success" fullWidth size="large" onClick={handleSign} disabled={!pdfFile}>Sign PDF</Button>
                        </Grid>
                        <Grid item xs={12} md={7}>
                            <Box sx={{ height: 600, bgcolor: '#525659', borderRadius: 2 }}>
                                {signedUrl ? <iframe src={signedUrl} width="100%" height="100%" /> : null}
                            </Box>
                            {signedUrl && <Button href={signedUrl} download="signed.pdf" startIcon={<Download />} sx={{ mt: 2 }}>Download</Button>}
                        </Grid>
                    </Grid>
                ) : (
                    <Box maxWidth="600px" mx="auto">
                        <Button component="label" variant="outlined" fullWidth sx={{ height: 100, borderStyle: 'dashed' }}>
                            {verifyFile ? verifyFile.name : "Upload PDF to Verify"}
                            <input type="file" hidden accept="application/pdf" onChange={(e) => setVerifyFile(e.target.files?.[0] || null)} />
                        </Button>
                        <Button variant="contained" fullWidth sx={{ mt: 2 }} onClick={handleVerify} disabled={!verifyFile}>Verify</Button>
                        {verifyResult && (
                            <Paper sx={{ mt: 3, p: 2, bgcolor: verifyResult.isValid ? '#e8f5e9' : '#ffebee' }}>
                                <Box display="flex" alignItems="center" gap={1} mb={2}>
                                    {verifyResult.isValid ? <CheckCircle color="success" /> : <ErrorIcon color="error" />}
                                    <Typography variant="h6">{verifyResult.isValid ? "VALID" : "INVALID"}</Typography>
                                </Box>
                                <Typography><strong>Subject:</strong> {verifyResult.signerSubject}</Typography>
                                <Typography><strong>Issuer:</strong> {verifyResult.signerIssuer}</Typography>
                                <Typography><strong>Time:</strong> {verifyResult.signingTime?.toLocaleString()}</Typography>
                                {verifyResult.errors.map((e, i) => <Alert severity="error" key={i} sx={{ mt: 1 }}>{e}</Alert>)}
                            </Paper>
                        )}
                    </Box>
                )}
            </Paper>
        </Container>
    );
}