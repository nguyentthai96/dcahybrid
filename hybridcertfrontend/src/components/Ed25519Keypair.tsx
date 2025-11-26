
import { useState } from "react";
import {useDidStore} from "../store/useDidStore.ts";
import type {Ed25519DidResponse} from "../types/did.ts";
import { Button, Card, CardContent } from "@mui/material";

export default function Ed25519Keypair() {
    const setKeypair = useDidStore((s) => s.setKeypair);
    const setDidDoc = useDidStore((s) => s.setDidDoc);
    const setJwk = useDidStore((s) => s.setJwk);

    const [loading, setLoading] = useState(false);

    const generate = async () => {
        try {
            setLoading(true);

            const res = await fetch("http://localhost:5000/did/ed25519");
            if (!res.ok) throw new Error("Request failed");

            const data: Ed25519DidResponse = await res.json();

            setKeypair(data.keypair);
            setDidDoc(data.didDocument);
            setJwk(data.jwk);
        } catch (err) {
            console.error("Generate DID error:", err);
            alert("Failed generating DID");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="shadow-xl rounded-2xl mt-4">
            <CardContent>
                <h2 className="text-xl font-bold">Ed25519 Keypair</h2>

                <Button
                    variant="contained"
                    onClick={generate}
                    disabled={loading}
                    sx={{ mt: 2 }}
                >
                    {loading ? "Generating..." : "Generate Ed25519 DID"}
                </Button>
            </CardContent>
        </Card>
    );
}
