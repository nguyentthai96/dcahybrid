import {Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography} from "@mui/material";

interface CertificateAlertProps {
    open: boolean;
    onClose: () => void;
    onOk: () => void;
}

export default function CertificateIssuedAlert({open, onClose, onOk }: CertificateAlertProps) {

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>Cấp phát thành công (Certificate Issued)</DialogTitle>
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
    );
}
