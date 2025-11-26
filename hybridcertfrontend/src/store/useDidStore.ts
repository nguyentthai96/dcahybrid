import { create } from "zustand";

export interface Keypair {
    publicKey: Uint8Array | string;   // encode
    secretKey?: Uint8Array | string;  // optional nếu không lưu
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
    y?: string;  // với Ed25519 chỉ cần x
    d?: string;
}

export interface DidState {
    keypair: Keypair | null;
    didDoc: DidDocument | null;
    jwk: Jwk | null;
    signature: string | null;
    ctRoot: string | null,

    setKeypair: (kp: Keypair | null) => void;
    setDidDoc: (doc: DidDocument | null) => void;
    setJwk: (jwk: Jwk | null) => void;
    setSignature: (sig: string | null) => void;
}

// -----------------------------
// 2) Create Store
// -----------------------------
export const useDidStore = create<DidState>((set) => ({
    keypair: null,
    didDoc: null,
    jwk: null,
    signature: null,
    ctRoot: null,

    //
    setKeypair: (kp) => set({ keypair: kp }),
    setDidDoc: (doc) => set({ didDoc: doc }),
    setJwk: (jwk) => set({ jwk }),
    setSignature: (sig) => set({ signature: sig }),
    // setCtRoot: (root) => set({ ctRoot: root }),
}));