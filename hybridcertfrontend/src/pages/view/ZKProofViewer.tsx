import {useState, useCallback} from "react";
import {Button, Card, CardContent, TextField} from "@mui/material";

interface ZKProofResponse {
    proof: unknown;
    pub: unknown;
}

export default function ZKProofViewer() {
    const [priv, setPriv] = useState("");
    const [proof, setProof] = useState<unknown | null>(null);
    const [pub, setPub] = useState<unknown | null>(null);

    const prove = useCallback(async () => {
        try {
            const body = priv ? {priv} : {};
            const res = await fetch("http://localhost:5000/zk/schnorr/prove", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json: ZKProofResponse = await res.json();
            setProof(json.proof);
            setPub(json.pub);
            alert("Proof generated (demo)");
        } catch (err) {
            console.error("Prove error:", err);
            alert("Failed to generate proof");
        }
    }, [priv]);

    const verify = useCallback(async () => {
        if (!proof || !pub) {
            alert("No proof/public");
            return;
        }
        try {
            const res = await fetch("http://localhost:5000/zk/schnorr/verify", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({proof, pub}),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json: { valid: boolean } = await res.json();
            alert(json.valid ? "✅ ZK Proof Verified" : "❌ Invalid");
        } catch (err) {
            console.error("Verify error:", err);
            alert("Failed to verify proof");
        }
    }, [proof, pub]);

    return (
        <Card className="mt-4 shadow-xl rounded-xl">
            <CardContent>
                <h3 className="text-lg font-bold">Schnorr ZK Proof (demo)</h3>

                <TextField
                    fullWidth
                    placeholder="Optional private key (b64url) for demo"
                    value={priv}
                    onChange={(e) => setPriv(e.target.value)}
                    className="mt-2"
                />

                <div className="mt-2 flex gap-2">
                    <Button variant="contained" onClick={prove}>
                        Prove
                    </Button>
                    <Button variant="outlined" onClick={verify}>
                        Verify
                    </Button>
                </div>

                <>
                    {proof && (
                        <pre className="mt-2 bg-white p-3 rounded break-words">
                            {JSON.stringify({
                                proof,
                                pub
                            }, null, 2)}</pre>
                    )}
                </>
            </CardContent>
        </Card>
    );
}
