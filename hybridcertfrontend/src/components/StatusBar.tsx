import React from 'react';
import {Box, Button, ButtonGroup, Tooltip, Typography} from '@mui/material';
import {ContentCopy, Download } from "@mui/icons-material";
import {CertificateDetails} from "./CertificateDetails.tsx";
import {X509Certificate} from "@peculiar/x509";
import {Convert} from "pvtsutils";
interface Props {
    status: { merkle_root: string; total_certs: number, dca_certificate:string };
    setParsedCertSysDetails?: (details: CertificateDetails) => void;
}

const StatusBar: React.FC<Props> = ({ status, setParsedCertSysDetails }) => {

    const handleCopy = () => {
        (async () => {
            console.log("download enrollCertificate", status.dca_certificate);
            await navigator.clipboard.writeText(status.dca_certificate);
        })();
    }
    const handleDownload = () => {
        (async () => {
            console.log("download enrollCertificate", status.dca_certificate);
            const cert = new X509Certificate(status.dca_certificate);
            const thumbprint = await cert.getThumbprint();
            const blob = new Blob([cert.toString("pem")], {
                type: "application/x-x509-ca-cert",
            });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${Convert.ToHex(thumbprint)}.pem`;
            a.download = "hybrid_dca_root.crt.pem";  // default filename
            a.click();
            window.URL.revokeObjectURL(url);
        })();
    };

    return (
        <Box className="bg-blue-900 text-white p-4 rounded-lg text-sm"
             display="flex"
             flexDirection="column"
             alignItems="flex-start"
        >
            <Box className="bg-blue-900 text-white p-4 rounded-lg text-sm"
                 display="grid"
                 gridTemplateColumns="1fr 1fr"
                 p="5px 50px"
                 gap={2}
            >
                <Typography>
                    <strong>Merkle Root:</strong> {status.merkle_root ? status.merkle_root.substring(0, 20) + '...' : 'Empty'}
                </Typography>

                <Typography>
                    <strong>Tổng Certs:</strong> {status.total_certs}   <a target="_blank" rel="noopener noreferrer" href="https://app.tryethernal.com/transactions">Tnx link</a>
                </Typography>
            </Box>
            <Box>
                <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ flexGrow: 1 }} >
                        <Typography  variant='subtitle1'>Thông tin Chứng chỉ gốc:</Typography>
                    </Box>
                    <ButtonGroup variant="outlined" size="small" color="primary">
                        <Tooltip title="Copy certificate to clipboard">
                            <Button onClick={handleCopy}>
                                <ContentCopy fontSize="small" />
                            </Button>
                        </Tooltip>
                        <Tooltip title="Download CA Certificate">
                            <Button onClick={handleDownload} size="small">
                                dca_root.crt.pem<Download fontSize="small" />
                            </Button>
                        </Tooltip>

                        {/*<Tooltip title="Remove CA">
                        <Button onClick={handleRemove} size="small">
                            <DeleteForever fontSize="small" />
                        </Button>
                    </Tooltip>*/}
                    </ButtonGroup>
                </Box>
                <CertificateDetails certificate={status.dca_certificate} />
            </Box>

        </Box>
    )
};

export default StatusBar;
