import { useState } from 'react';

export interface SignResult {
    hash: string;
    signature: string;
    pubkey: string;
}

export const useFileSigner = () => {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<SignResult | null>(null);

    const sign = async () => {
    console.log("Handler sign click......")
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('http://localhost:5000/sign', { method: 'POST', body: formData });
        setResult(await res.json());
    };

    const verify = async () => {
        if (!file || !result) return alert('File empty! Please sign the file first.');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('signature', result.signature);
        formData.append('pubkey', result.pubkey);
        const res = await fetch('http://localhost:5000/verify', {
         method: 'POST',
         body: formData
         });
        const json = await res.json() as { valid: boolean };
        alert(json.valid ? '✅ Verified' : '❌ Invalid Signature');
    };

    return { file, setFile, result, sign, verify };
};
