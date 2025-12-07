import {useState} from 'react';
import {Alert, Box, Button, CircularProgress, Container, Divider, Grid, Paper, Typography} from '@mui/material';
import {Download, PictureAsPdf, VerifiedUser, VpnKey} from '@mui/icons-material';
import {signPdfPAdES} from '../pdfSigning';
import FileUploadBox from "./FileUploadBox.tsx";


export default function PdfSigner() {
    const [privateKeyFile, setPrivateKeyFile] = useState<File | null>(null);
    const [privateKeyText, setPrivateKeyText] = useState("");
    const [userCertFile, setUserCertFile] = useState<File | null>(null);
    const [userCertText, setUserCertText] = useState("");
    const [caCertFile, setCaCertFile] = useState<File | null>(null);
    const [caCertText, setCaCertText] = useState("");
    const [pdfFile, setPdfFile] = useState<File | null>(null);

    const [loading, setLoading] = useState(false);
    const [signedPdfUrl, setSignedPdfUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleSign = async () => {
        if (!privateKeyText || !userCertText || !pdfFile) {
            setError("Please upload Private Key, User Certificate and a PDF file.");
            return;
        }
        setError(null);
        setLoading(true);

        try {
            const pdfBuffer = await pdfFile.arrayBuffer();

            // Gọi hàm ký
            const signedPdfBytes = await signPdfPAdES(
                pdfBuffer,
                privateKeyText,
                userCertText,
                caCertText || undefined
            );

            // Tạo Blob URL
            const blob = new Blob([signedPdfBytes as any], { type: "application/pdf" });
            const url = URL.createObjectURL(blob);
            setSignedPdfUrl(url);

        } catch (err: any) {
            console.error(err);
            setError("Signing failed: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Paper elevation={3} sx={{ p: 4, borderRadius: 3 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                    React PDF Signing (PAdES / ECDSA secp256k1)
                </Typography>

                <Grid container spacing={4} sx={{ mt: 1 }}>
                    <Grid item xs={12} md={5}>
                        <FileUploadBox
                            label="Private Key (PEM)"
                            file={privateKeyFile} setFile={setPrivateKeyFile}
                            textContent={privateKeyText} setTextContent={setPrivateKeyText}
                            icon={<VpnKey />} accept=".pem,.key"
                        />
                        <FileUploadBox
                            label="User Certificate (PEM)"
                            file={userCertFile} setFile={setUserCertFile}
                            textContent={userCertText} setTextContent={setUserCertText}
                            icon={<VerifiedUser />} accept=".pem,.crt"
                        />
                        <FileUploadBox
                            label="CA Chain (Optional)"
                            file={caCertFile} setFile={setCaCertFile}
                            textContent={caCertText} setTextContent={setCaCertText}
                            icon={<VerifiedUser color="action"/>} accept=".pem,.crt"
                        />

                        <Divider sx={{ my: 3 }} />

                        <Box sx={{ mb: 3 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                                <PictureAsPdf /> Document to Sign
                            </Typography>
                            <Button
                                variant="outlined"
                                component="label"
                                fullWidth
                                sx={{ height: 60, borderStyle: 'dashed' }}
                            >
                                {pdfFile ? pdfFile.name : "Select PDF File"}
                                <input
                                    type="file"
                                    hidden
                                    accept="application/pdf"
                                    onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                                />
                            </Button>
                        </Box>

                        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                        <Button
                            variant="contained" size="large" fullWidth
                            onClick={handleSign} disabled={loading}
                            startIcon={loading ? <CircularProgress size={20} color="inherit"/> : <VerifiedUser />}
                        >
                            {loading ? "Signing..." : "Sign Document"}
                        </Button>
                    </Grid>

                    <Grid item xs={12} md={7}>
                        <Box sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
                            <Typography variant="h6" gutterBottom>Preview</Typography>
                            <Box sx={{ flex: 1, border: '1px solid #ddd', borderRadius: 2, overflow: 'hidden', bgcolor: '#525659' }}>
                                {signedPdfUrl ? (
                                    <iframe src={signedPdfUrl} width="100%" height="100%" style={{ border: 'none' }} title="Signed PDF"/>
                                ) : (
                                    <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
                                        {pdfFile ? "PDF Loaded. Ready to sign." : "No PDF loaded"}
                                    </Box>
                                )}
                            </Box>
                            {signedPdfUrl && (
                                <Button
                                    variant="contained" color="success" sx={{ mt: 2 }}
                                    href={signedPdfUrl} download={`signed_${pdfFile?.name || 'doc.pdf'}`}
                                    startIcon={<Download />}
                                >
                                    Download Signed PDF
                                </Button>
                            )}
                        </Box>
                    </Grid>
                </Grid>
            </Paper>
        </Container>
    );
}