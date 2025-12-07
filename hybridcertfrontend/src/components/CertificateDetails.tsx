import {Table, TableBody, TableCell, TableContainer, TableRow, Typography} from "@mui/material";
import {X509Certificate} from "@peculiar/x509";
import * as React from "react";
import {Convert} from "pvtsutils";

export interface CertificateDetailsProps {
    certificate: string | X509Certificate;
    onParsedCertSys?: (details: CertificateDetails) => void;
}

export interface CertificateDetails {
    serialNumber: string;
    subject: string;
    issuer: string;
    validityDays: number;
    leftDays: number;
    algorithm: string;
    thumbprint: Record<string, string>;
}

export const CertificateDetails: React.FC<CertificateDetailsProps> = ({certificate, onParsedCertSys}) => {
    const [details, setDetails] = React.useState<CertificateDetails>();
    console.log("CertificateDetails.tsx data certificate", certificate);
    React.useEffect(() => {
        (async () => {
            const cert = typeof certificate === 'string' ? new X509Certificate(certificate) : certificate;
            console.log("CertificateDetails.tsx useEffect ECDSA details cert", cert);
            const thumbprint = await cert.getThumbprint("SHA-256");
            const certVal = {
                leftDays: (cert.notAfter.getTime() - Date.now()) / (1000 * 60 * 60 * 24),
                validityDays: (cert.notAfter.getTime() - cert.notBefore.getTime()) / (1000 * 60 * 60 * 24),
                serialNumber: cert.serialNumber,
                subject: cert.subject,
                issuer: cert.issuer,
                algorithm: `ECDSA ${(cert.publicKey.algorithm as EcKeyAlgorithm).namedCurve}`,
                thumbprint: {
                    "SHA-256": Convert.ToHex(thumbprint),
                }
            }
            setDetails(certVal);
            if (onParsedCertSys) onParsedCertSys(certVal);
        })()
            .catch((e) => {
                console.error(e);
                alert(e);
            });
    }, [certificate]);

    return (
        <TableContainer>
            {
                !details ? (
                    <Typography  variant='body2'>Loading...</Typography>
                ) : (
                    <Table size="small">
                        <TableBody>
                            <TableRow>
                                <TableCell>Serial Number</TableCell>
                                <TableCell>{details.serialNumber}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableCell>Subject</TableCell>
                                <TableCell>{details.subject}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableCell>Issuer</TableCell>
                                <TableCell>{details.issuer}</TableCell>
                            </TableRow>
                            {/*<TableRow>*/}
                            {/*    <TableCell>Validity (days)</TableCell>*/}
                            {/*    <TableCell>{`${details.validityDays} (${details.leftDays.toFixed(0)} left)`}</TableCell>*/}
                            {/*</TableRow>*/}
                            <TableRow>
                                <TableCell>Public Key</TableCell>
                                <TableCell>{details.algorithm}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableCell>Thumbprint</TableCell>
                                <TableCell>
                                    <Typography variant='body2'
                                                color='text.secondary'>SHA-256: {details.thumbprint["SHA-256"]}</Typography>
                                </TableCell>
                            </TableRow>
                        </TableBody>
                    </Table>
                )
            }
        </TableContainer>
    );
};