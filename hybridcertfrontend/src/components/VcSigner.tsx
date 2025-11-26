import {useState} from "react";
import { Button, Card, CardContent, TextField } from "@mui/material";
import { useDidStore } from "../store/useDidStore";

export default function VcSigner() {
    const [inputJson, setInputJson] = useState(
        `{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "id": "urn:uuid:example",
  "type": ["VerifiableCredential"],
  "issuer": "did:example:issuer",
  "issuanceDate": "2025-11-18T00:00:00Z",
  "credentialSubject": {
    "id": "did:example:recipient",
    "name": "Alice"
  }
}`
    );

    const setDidDoc = useDidStore(s => s.setDidDoc);
    const setJwk = useDidStore(s => s.setJwk);
    const setKeypair = useDidStore(s => s.setKeypair);
    const setSignature = useDidStore(s => s.setSignature);

    const sign = async () => {
        let credential;
        try {
            credential = JSON.parse(inputJson);
        } catch{
            alert("Invalid JSON format.");
            return;
        }

        const res = await fetch("http://localhost:5000/sign/vc", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ credential })
        });
        const json = await res.json();
        // store returned didDoc/jwk/ephemeral private if any
        setDidDoc(json.didDocument);
        setJwk(json.didDocument.verificationMethod[0].publicKeyJwk);
        setKeypair({
            // privateKey: json.ephemeral_privateKey,
            /// secretKey: json.ephemeral_privateKey, // ????
            publicKey: json.didDocument.verificationMethod[0].publicKeyJwk
        });
        setSignature(json.proof);
        alert("Credential signed (demo). Proof added.");
    };

    return (
        <Card className="mt-4 shadow-xl rounded-xl">
            <CardContent>
                <h3 className="text-lg font-bold">VC Signer (VCDM 2.0 demo)</h3>

                <TextField
                    multiline
                    minRows={6}
                    fullWidth
                    value={inputJson}
                    onChange={(e) => setInputJson(e.target.value)}
                />

                <div className="mt-2">
                    <Button variant="contained" onClick={sign}>Sign Credential</Button>
                </div>
            </CardContent>
        </Card>
    );
}
