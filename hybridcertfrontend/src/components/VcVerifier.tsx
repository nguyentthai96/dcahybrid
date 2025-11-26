import {useState} from "react";
import {Button, Card, CardContent, TextField} from "@mui/material";
import {useDidStore} from "../store/useDidStore";

export default function VcVerifier(){
    const [inputJson, setInputJson] = useState("");
    const didDoc = useDidStore(s => s.didDoc);
    const jwk = useDidStore(s => s.jwk);

    const verify = async () => {
        let credential
        try {
            credential = JSON.parse(inputJson) ;
        } catch{
            alert("Invalid JSON");
            return;
        }

        const body:any = { credential };
        if (didDoc) body.didDocument = didDoc;
        else if (jwk) {
            body.pubkey = jwk.x + jwk.y ? (jwk.x + jwk.y) : null;
        }
        const res = await fetch("http://localhost:5000/verify/vc", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        const json = await res.json();
        alert(json.valid ? "✅ Verified" : "❌ Invalid");
    };

    return (
        <Card className="mt-4">
            <CardContent>
                <h3 className="text-lg font-bold">VC Verifier (VCDM 2.0 demo)</h3>
                <TextField
                    multiline
                    minRows={6}
                    fullWidth
                    placeholder="Paste signed credential JSON with proof"
                    value={inputJson}
                    onChange={(e) => setInputJson(e.target.value)}
                />
                <div className="mt-2">
                    <Button variant="contained" onClick={verify}>Verify Credential</Button>
                </div>
            </CardContent>
        </Card>
    );
}
