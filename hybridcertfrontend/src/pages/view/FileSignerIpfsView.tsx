import {Card} from "@mui/material";
import {useState, useCallback} from "react";
import {ScrollArea} from "@radix-ui/react-scroll-area";
import {JsonTree} from "../../components/JsonTree.tsx";


interface SignResult {
    signature: unknown;
    certificate_pem?: string;
    pubkey_b64?: string;
    verify?: VerifyResult;

    [key: string]: unknown;
}

interface VerifyResult {
    valid: boolean;
    identity?: unknown;
    ipfs_cid?: string;
    eth_tx?: unknown;
}


export default function FileSignerIpfsView() {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<SignResult | null>(null);
    const [loading, setLoading] = useState(false);


    // --- Helpers ----------------------------------------------------
    const upload = useCallback(async (url: string, fd: FormData) => {
        const res = await fetch(url, {method: "POST", body: fd});
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }, []);

    // --- Sign -------------------------------------------------------
    const signFile = useCallback(async () => {
        if (!file) return;
        setLoading(true);

        try {
            const fd = new FormData();
            fd.append("file", file);
            //
            const json = await upload("http://localhost:5000/sign", fd);
            setResult(json);
        } catch (err) {
            console.error("Sign error:", err);
            alert("Failed to sign file");
        } finally {
            setLoading(false);
        }
    }, [file, upload]);

    // --- Verify & Store ---------------------------------------------
    // https://bitl.to/5L9E
    const verifyAndStore = useCallback(
        async (opts?: { store_ipfs?: boolean; store_chain?: boolean }) => {
            if (!file || !result) return;

            const {store_ipfs = false, store_chain = false} = opts || {};
            setLoading(true);

            try {
                const fd = new FormData();
                fd.append("file", file);
                fd.append("signature", JSON.stringify(result.signature));
                fd.append("certificate_pem", result.certificate_pem ?? "");
                fd.append("pubkey_b64", result.pubkey_b64 ?? "");
                fd.append("store_ipfs", String(store_ipfs));
                fd.append("store_chain", String(store_chain));

                const json: VerifyResult = await upload(
                    "http://localhost:5000/verify_and_store",
                    fd
                );

                setResult((prev) => (prev ? {...prev, verify: json} : prev));
            } catch (err) {
                console.error("Verify error:", err);
                alert("Failed to verify");
            } finally {
                setLoading(false);
            }
        },
        [file, result, upload]
    );

    // ----------------------------------------------------------------
    return (
        <div style={{padding: 20}}>
            <h2>DCA Demo — Sign & Verify</h2>

            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)}/>

            <div style={{marginTop: 8}}>
                <button onClick={signFile} disabled={!file || loading}>
                    Sign
                </button>

                <button onClick={() => verifyAndStore()} disabled={!result || loading}>
                    Verify
                </button>

                <button
                    onClick={() => verifyAndStore({store_ipfs: true})}
                    disabled={!result || loading}
                >
                    Verify + IPFS
                </button>

                <button
                    onClick={() =>
                        verifyAndStore({store_ipfs: true, store_chain: true})
                    }
                    disabled={!result || loading}
                >
                    Verify + IPFS + Chain
                </button>
            </div>

            {result && (
                <div style={{marginTop: 20, border: "1px solid #ddd", padding: 12}}>
                    <Card sx={{mt: 2, p: 2}}>
                        <h3>Signature Result</h3>
                        <ScrollArea className="h-64">
                            {/* npm install --save react-json-view-lite #### react-json-view-lite*/}
                            <pre className="bg-gray-50 p-2 rounded text-sm break-words"
                                 style={{whiteSpace: "pre-wrap"}}>
                                {JSON.stringify(result, null, 2)}
                            </pre>
                            <JsonTree data={result}/>
                        </ScrollArea>
                        <>
                            {result.verify && (
                                <>
                                    <h3>Verify & Storage</h3>
                                    <p>Valid: {String(result.verify.valid)}</p>
                                    <p>
                                        Identity:{" "}
                                        {result.verify.identity
                                            ? JSON.stringify(result.verify.identity)
                                            : "—"}
                                    </p>

                                    {result.verify.ipfs_cid && (
                                        <p>
                                            IPFS:{" "}
                                            <a
                                                href={`https://ipfs.io/ipfs/${result.verify.ipfs_cid}`}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                {result.verify.ipfs_cid}
                                            </a>
                                        </p>
                                    )}

                                    {result.verify.eth_tx && (
                                        <pre>{JSON.stringify(result.verify.eth_tx, null, 2)}</pre>
                                    )}
                                </>
                            )}
                        </>
                    </Card>
                </div>
            )}
        </div>
    );
}
