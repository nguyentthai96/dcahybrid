import {
    Box,
    Button,
    ButtonGroup,
    FormControl,
    InputLabel,
    List,
    ListItem,
    Step,
    StepLabel,
    Stepper,
    TextField,
    Tooltip,
    Typography,
} from "@mui/material";
import {v4 as uuidv4} from 'uuid';
import * as React from "react";
import {useState} from "react";
import {Pkcs10CertificateRequest, PublicKey, X509Certificate} from "@peculiar/x509";
import {Convert} from "pvtsutils";

import {CertificateDetails} from "./CertificateDetails";
import axios from "axios";
import {API_URL} from "../App.tsx";
import ResultJsonMetaCopyable from "./ResultJsonMetaCopyable.tsx";
import CertificateIssuedAlert from "./CertificateIssuedAlert.tsx";
import {ContentCopy, Download} from "@mui/icons-material";

export interface IssueCertificateProps {
    parsedCertSysDetails: CertificateDetails
    fetchStatus: () => void;
}

export const IssueCertificate: React.FC<IssueCertificateProps> = ({parsedCertSysDetails, fetchStatus}) => {

        const [activeStep, setActiveStep] = React.useState<number>(0);
        const [csr, setCsr] = React.useState<PublicKey | null>(null);
        const [certName, setCertName] = React.useState<string>(
            "CN=, O=, C=VN, E="
        );
        const [ownerInfoOrId, setOwnerInfoOrId] = React.useState<string>('');
        // const [certValidity, setCertValidity] = React.useState<number>(365);
        const fileInputRef = React.useRef<HTMLInputElement>(null);
        const [fileCsr, setFileCsr] = React.useState<File | null>(null); // to set edit public view
        const [isDragOver, setIsDragOver] = React.useState(false);


        //
        const [alertOpen, setAlertOpen] = React.useState(false);
        const [signResult, setSignResult] = useState<any>(null);

        const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            setIsDragOver(true);
        };

        const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            setIsDragOver(false);
        };


        /*const enrollCertificate = async (key: x509.PublicKey, value: any,
                                         params: CaEnrolParams) => {
            if (!value) {
                throw new Error("CA is not initialized");
            }
            console.log("enrollCertificate");
            console.log("value.cert", value);
            const caCert = new x509.X509Certificate(value);

            const serial = crypto.getRandomValues(new Uint8Array(16));
            serial[0] &= 0x7f;
            if (serial[0] === 0) {
                serial[1] |= 0x80;
            }

            const certParams: x509.X509CertificateCreateParams = {
                serialNumber: Convert.ToHex(serial),
                subject: params.subject,
                issuer: caCert.subject,
                // notBefore:  new Date(2025,10,1,0,0,0,0),
                // notAfter: new Date(Date.now() + 1000 * 60 * 60 * 24 * params.validity),
                signingAlgorithm: {
                    hash: "SHA-256",
                    ...caCert.publicKey.algorithm,
                },
                publicKey: key,
                signingKey: value.key,
                extensions: [
                    new x509.BasicConstraintsExtension(false, undefined, true),
                    await x509.AuthorityKeyIdentifierExtension.create(caCert),
                    await x509.SubjectKeyIdentifierExtension.create(key),
                ],
            };
            const extensions = certParams.extensions || [];
            // case "pdf_signing":
            extensions.push(
                new x509.KeyUsagesExtension(
                    x509.KeyUsageFlags.digitalSignature,
                    true
                )
            );
            extensions.push(
                new x509.ExtendedKeyUsageExtension(["1.2.840.113583.1.1.10"])
            ); // Adobe PDF

            return await x509.X509CertificateGenerator.create(certParams);
        }*/

        React.useEffect(() => {
            if (fileCsr) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    setSignResult(null);
                    const contents = e.target?.result;
                    if (contents instanceof ArrayBuffer) {
                        const view = new Uint8Array(contents);
                        const bufOrStr =
                            view[0] === 0x30 ? contents : Convert.ToBinary(contents);
                        try {
                            const cert = new X509Certificate(bufOrStr);
                            setCsr(cert.publicKey);
                            console.log("X509Certificate readCsrFile cert subject", cert);
                            setCertName(cert.subject);
                        } catch {
                            try {
                                const publicKey = new PublicKey(bufOrStr);
                                setCsr(publicKey);
                            } catch {
                                try {
                                    const csr = new Pkcs10CertificateRequest(bufOrStr);
                                    setCsr(csr.publicKey);
                                    console.log("Pkcs10CertificateRequest readCsrFile cert subject ", csr);
                                    setCertName(csr.subject);
                                } catch (e) {
                                    alert("Invalid Public Key, X509 or CSR");
                                    return;
                                }
                            }
                        }
                    }
                };
                reader.readAsArrayBuffer(fileCsr);
            }else{
                setSignResult(null);
            }
        }, [fileCsr]);


        const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            if (e.dataTransfer.items) {
                for (let i = 0; i < e.dataTransfer.items.length; i++) {
                    if (e.dataTransfer.items[i].kind === "file") {
                        setFileCsr(e.dataTransfer.items[i].getAsFile());
                    }
                }
            }
        };

        const handleCsrChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const value = e.target.value;
            try {
                const cert = new X509Certificate(value);
                setCsr(cert.publicKey);
            } catch {
                try {
                    const publicKey = new PublicKey(value);
                    setCsr(publicKey);
                } catch {
                    try {
                        const csr = new Pkcs10CertificateRequest(value);
                        setCsr(csr.publicKey);
                    } catch (e) {
                        alert("Invalid Public Key, X509 or CSR");
                        return;
                    }
                }
            }
        };

        const handleSign = async () => {
            if (!csr) {
                alert("CSR is empty, please paste a valid CSR, to get Public Key or X509")
                return;
            }
            if (!fileCsr) return alert("CSR is empty, please paste a valid CSR, to get Public Key or X509");
            if (!ownerInfoOrId) setOwnerInfoOrId(uuidv4())/*return alert("Owner info is empty, please provide owner info");*/
            const formData = new FormData();
            formData.append('file', fileCsr);
            formData.append('metadata', ownerInfoOrId || "No description");

            try {
                const res = await axios.post(`${API_URL}/issue`, formData);
                setSignResult(res.data);
                setAlertOpen(true);
                if (res.data) {
                    fetchStatus();
                }
            } catch (err) {
                alert("Ký số thất bại (Signing failed)");
            }
        };

        const handleCopy = () => {
            (async () => {
                console.log("download enrollCertificate", signResult.certificate_crt_pem);
                await navigator.clipboard.writeText(atob(signResult.certificate_crt_pem));
            })();
        }

        const downloadCertIssuedHandler = () => {
            (async () => {
                console.log("download enroll issued Certificate", signResult.certificate_crt_pem);
                if (!signResult || !signResult.certificate_crt_pem) {
                    alert("No certificate to download.");
                }
                const cert = new X509Certificate(atob(signResult.certificate_crt_pem));
                const thumbprint = await cert.getThumbprint();
                const blob = new Blob([cert.toString("pem")]);
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                const originalName = fileCsr?.name.replace(/\.[^/.]+$/, "") ?? "uploaded";
                a.download = `${ownerInfoOrId.substring(0,8)}_user_crt_${originalName}_${Convert.ToHex(thumbprint).substring(0, 8)}.crt.pem`;
                a.click();
                window.URL.revokeObjectURL(url);
                setAlertOpen(false);
            })();
        }

        const handleImportCsr = () => {
            if (!csr) {
                alert("CSR is empty, please paste a valid CSR, to get Public Key or X509")
                return;
            }

            setActiveStep(1);
        };

        const handleBack = () => {
            setActiveStep(activeStep - 1);
        };


        // const handleCertValidityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        //     setCertValidity(parseInt(e.target.value));
        // };


        const handleIssue = (value: any) => {
            (async () => {
                if (!csr) {
                    alert("CSR is empty, please paste a valid CSR, Public Key or X509")
                    return;
                }
                try {



                    setActiveStep(2);
                } catch (e) {
                    alert(`Failed to issue certificate: ${e}`);
                    return;
                }
            })();
        };




        const handleCopyPem = () => {
            navigator.clipboard.writeText(cert);
        };

        return (
            <Box sx={{mt: 2}}>
                <Box>
                    <Stepper activeStep={activeStep} sx={{mt: 2, mb: 2}}>
                        <Step>
                            <StepLabel>Import CSR</StepLabel>
                        </Step>
                        <Step>
                            <StepLabel>Issued Certificate</StepLabel>
                        </Step>
                        <Step>
                            <StepLabel>Done</StepLabel>
                        </Step>
                    </Stepper>
                </Box>
                {activeStep === 0 && ( // Import CSR
                    <Box sx={{mt: 2}}>
                        <Box gap={2}>
                            <Typography sx={{display: "flex", alignItems: "left", flexDirection: "column"}}>
                                <Box sx={{display: "flex", alignItems: "left",}}>
                                    Cung cấp CSR, hoặc dán Khóa công khai hoặc chứng chỉ X509
                                    (Có thể dùng openssl để tạo theo lệnh)
                                </Box>
                                <Box sx={{
                                    bgcolor: 'grey.100', alignItems: "left", display: "flex-start", textAlign: 'left',
                                    m: 0, // Thêm margin-top cho dễ nhìn
                                }}>
                                    - Tạo khóa bí mật ECDSA cho chứng chỉ con (user_key.key.pem) <br/>
                                    <code>openssl ecparam -name secp256k1 -genkey -noout -out user_key.key.pem</code>
                                    <br/>
                                    - Tạo yêu cầu ký chứng chỉ (CSR) cho chứng chỉ con (user_cert.csr.pem) <br/>
                                    <code>openssl req -new -sha256 -key user_key.key.pem -out user_cert.csr.pem -subj
                                        "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"</code>
                                </Box>
                            </Typography>
                            <List sx={{width: "100%"}}>
                                <ListItem>
                                    <TextField
                                        label="Metadata - Tên sở hữu, ID..."
                                        value={ownerInfoOrId}
                                        onChange={(e) => setOwnerInfoOrId(e.target.value)}
                                        placeholder="Ví dụ: Alice - ID 12345"
                                        size="small"
                                        sx={{width: "100%"}}
                                        slotProps={{
                                            input: {
                                                style: {fontSize: "12px"},
                                            }
                                        }}
                                    />
                                </ListItem>
                                <ListItem>
                                    <TextField
                                        label="Subject Name"
                                        value={certName}
                                        onChange={(e) => setCertName(e.target.value)}
                                        size="small"
                                        sx={{width: "100%"}}
                                        slotProps={{
                                            input: {
                                                readOnly: true,
                                                style: {fontSize: "12px"},
                                            }
                                        }}
                                    />
                                </ListItem>
                            </List>
                            <Box gap={2} sx={{display: "flex", flexDirection: "row"}}>
                                <Box flex={1}
                                     onDrop={(e) => {
                                         handleDrop(e);
                                         setIsDragOver(false);
                                     }}
                                     onDragOver={(e) => e.preventDefault()}
                                     onDragEnter={handleDragEnter}
                                     onDragLeave={handleDragLeave}
                                     onClick={() => fileInputRef.current?.click()}
                                     sx={{
                                         border: isDragOver ? "2px dashed lightblue" : "2px dashed gray",
                                         padding: 2,
                                         display: "flex",
                                         flexDirection: "column",
                                         alignItems: "center",
                                         justifyContent: "center",
                                         minHeight: "100px",
                                         m: 2,
                                         cursor: "pointer",
                                     }}
                                     gap={1}
                                >
                                    <Typography
                                        variant="body2"
                                        sx={{pointerEvents: "none"}}
                                    >
                                        {(!fileCsr) ? "Drag and drop the CSR, Public Key or X509 certificate here or click here to upload." : fileCsr?.name}
                                    </Typography>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        style={{display: "none"}}
                                        onChange={(e) => setFileCsr(e.target.files?.[0] || null)}
                                    />
                                </Box>
                                <Box sx={{display: 'inline-flex'}} flex={5}>
                                    {/* public key input from csr file */}
                                    <TextField
                                        multiline
                                        fullWidth
                                        rows={10}
                                        value={csr}
                                        onChange={handleCsrChange}
                                        slotProps={{
                                            input: {
                                                readOnly: true,
                                                style: {fontFamily: "Monaco, monospace", fontSize: "12px"},
                                            }
                                        }}
                                    />
                                </Box>
                            </Box>
                        </Box>

                        <Box sx={{display: "flex", justifyContent: "flex-end", mt: 2}}>
                            {(!signResult) && <Button onClick={handleSign}>Cấp chứng chỉ (Issue Certificate)</Button>}
                            {(signResult) && (
                                <Button onClick={handleImportCsr}>Xem chứng chỉ (Issued Certificate)</Button>)}
                        </Box>

                        {signResult && (
                            <ResultJsonMetaCopyable dataJson={signResult}/>
                        )}
                        <CertificateIssuedAlert
                            open={alertOpen}
                            onClose={() => setAlertOpen(false)}
                            onOk={() => downloadCertIssuedHandler()}
                        />
                    </Box>
                )}
                {activeStep === 1 && ( // Issue Certificate
                    <Box>
                        <Box sx={{display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 2}}>
                            <Box sx={{flexGrow: 1}}>
                                <Typography variant='subtitle1'>Thông tin Chứng chỉ người dùng sở hữu ký bởi
                                    DCA:</Typography>
                            </Box>
                            <ButtonGroup variant="outlined" size="small" color="primary">
                                <Tooltip title="Copy certificate to clipboard">
                                    <Button onClick={handleCopy}>
                                        <ContentCopy fontSize="small"/>
                                    </Button>
                                </Tooltip>
                                <Tooltip title="Download User Certificate">
                                    <Button onClick={downloadCertIssuedHandler} size="small">
                                        user_certificate_issued.crt.pem<Download fontSize="small"/>
                                    </Button>
                                </Tooltip>
                            </ButtonGroup>
                        </Box>
                        <ListItem>
                            <TextField
                                label="Metadata - Tên sở hữu, ID..."
                                value={ownerInfoOrId}
                                onChange={(e) => setOwnerInfoOrId(e.target.value)}
                                placeholder="Ví dụ: Alice - ID 12345"
                                size="small"
                                sx={{width: "100%"}}
                                slotProps={{
                                    input: {
                                        readOnly: true,
                                        style: {fontSize: "12px"},
                                    }
                                }}
                            />
                        </ListItem>
                        <CertificateDetails certificate={atob(signResult.certificate_crt_pem)}/>

                        <Box
                            sx={{display: "flex", justifyContent: "flex-end", mt: 2, gap: 1}}
                        >
                            <Button onClick={handleBack}>Cấp phát mới</Button>
                            <Button onClick={handleIssue}>Issue</Button>
                        </Box>

                        {signResult && (
                            <ResultJsonMetaCopyable dataJson={signResult}/>
                        )}
                    </Box>
                )}
                {activeStep === 2 && ( // Done
                    <Box>
                        <Typography variant="body2" paragraph>
                            Certificate issued successfully.
                        </Typography>
                        <CertificateDetails certificate={atob(signResult.certificate_crt_pem)}/>
                        <Box sx={{mt: 2}}>
                            <Typography variant="body2" paragraph>
                                Issued certificate in PEM format:
                            </Typography>
                            <TextField
                                multiline
                                fullWidth
                                rows={10}
                                value={atob(signResult.certificate_crt_pem)}
                                InputProps={{
                                    readOnly: true,
                                    style: {fontFamily: "Monaco, monospace", fontSize: "12px"},
                                }}
                            />
                        </Box>
                        <Box
                            sx={{display: "flex", justifyContent: "flex-end", mt: 2, gap: 1}}
                        >
                            <Button onClick={handleBack}>Xem chứng chỉ (Issued Certificate)</Button>
                            <Button onClick={handleCopyPem}>Copy</Button>
                        </Box>
                    </Box>
                )}
            </Box>
        );
    }
;
