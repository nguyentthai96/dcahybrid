import {Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography} from "@mui/material";

interface CertificateAlertProps {
    open: boolean;
    onClose: () => void;
    onOk: () => void;
}

export default function CertificateIssuedAlert({open, onClose, onOk }: CertificateAlertProps) {

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>Certificate Issued</DialogTitle>
            <DialogContent>
                <Typography fontSize={14}>
                    ✅ Chứng chỉ đã phát hành thành công (Certificate Issued)!
                    Bạn có thể tải về và tiếp tục các bước tiếp theo.
                </Typography>
            </DialogContent>
            <DialogActions>
                <Button variant="outlined" onClick={onClose}>Close</Button>
                <Button variant="contained" onClick={onOk}>OK</Button>
            </DialogActions>
        </Dialog>
        /*<Alert
            severity="success"
            onClose={onClose}
            variant="filled"
            sx={{
                position: "fixed",
                top: 20,
                right: 20,
                width: "360px",
                zIndex: 9999
            }}
        >
            <AlertTitle>Chứng chỉ đã được cấp phát</AlertTitle>
            Bạn có thể tải xuống chứng chỉ và tiến hành bước tiếp theo.

            {certificateUrl && (
                <Button
                    sx={{mt: 1}}
                    href={certificateUrl}
                    download="user_crt.crt.pem"
                    color="inherit"
                    variant="outlined"
                >
                    Tải chứng chỉ
                </Button>
            )}

            <Stack direction="row" spacing={2} sx={{mt: 2}}>
                <Button variant="outlined" onClick={onClose}>
                    Close
                </Button>
                <Button variant="contained" onClick={onOk}>
                    OK
                </Button>
            </Stack>
        </Alert>*/
    );
}
