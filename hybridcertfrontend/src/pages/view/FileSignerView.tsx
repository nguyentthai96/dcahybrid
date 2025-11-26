import React from "react";

interface FileSignVerifyViewProps {
    file: File | null;
    result: { hash: string; signature: string; pubkey: string } | null;
    onFileChange: (file: File) => void;
    onSign: () => void;
    onVerify: () => void;
}

/**
 const {file, setFile, result, sign, verify} = useFileSigner();
 <FileSignVerifyView
     file={file}
     result={result}
     onFileChange={setFile}
     onSign={sign}
     onVerify={verify}
 />
 */
const FileSignVerifyView: React.FC<FileSignVerifyViewProps> = ({
                                                                   file,
                                                                   result,
                                                                   onFileChange,
                                                                   onSign,
                                                                   onVerify,
                                                               }) => {
    return (

        <div style={{ padding: 20 }}>
            <h1 className="text-3xl font-bold">Decentralized CA Demo</h1>
            <input type="file" onChange={(e) => e.target.files && onFileChange(e.target.files[0])} />
            <button onClick={onSign} disabled={!file}>Sign</button>
            <button onClick={onVerify} disabled={!result}>Verify</button>
            {result && (
                <div style={{ marginTop: 20 }}>
                    <p><b>File Hash:</b> {result.hash}</p>
                    <p><b>Signature:</b> {result.signature}</p>
                    <p><b>Public Key:</b> {result.pubkey}</p>
                </div>
            )}
        </div>

    );
};


export default FileSignVerifyView;