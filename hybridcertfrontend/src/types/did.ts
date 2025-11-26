export interface Ed25519Keypair {
    publicKey: string;   // base64
    secretKey?: string;  // base64 (nếu backend trả)
}

export interface DidDocument {
    id: string;
    controller?: string;
    verificationMethod?: any[];
    authentication?: any[];
    [k: string]: any;
}

export interface Jwk {
    kty: string;
    crv: string;
    x: string;
    d?: string;
}

export interface Ed25519DidResponse {
    keypair: Ed25519Keypair;
    didDocument: DidDocument;
    jwk: Jwk;
}
