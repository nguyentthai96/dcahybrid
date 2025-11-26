import {Button, Card, CardContent } from "@mui/material";
import {type DidDocument, type Jwk, type Keypair, useDidStore} from "../store/useDidStore.ts";

export default function Secp256k1Keypair() {
    const setKeypair = useDidStore((s) => s.setKeypair);
    const setDidDoc = useDidStore((s) => s.setDidDoc);
    const setJwk = useDidStore((s) => s.setJwk);

    const generate = async () => {
        const res = await fetch("http://localhost:5000/did/secp256k1");
        const data = await res.json()  as {
            keypair: Keypair,
            didDocument: DidDocument,
            jwk: Jwk
        };

        setKeypair(data.keypair);
        setDidDoc(data.didDocument);
        setJwk(data.jwk);
    };

    return (
        <Card className="shadow-xl rounded-2xl mt-4">
            <CardContent>
                <h2 className="text-xl font-bold">Secp256k1 Keypair</h2>
                <Button variant="contained" onClick={generate} sx={{ mt: 2 }}>
                    Generate Secp256k1 DID
                </Button>
            </CardContent>
        </Card>
    );
}
