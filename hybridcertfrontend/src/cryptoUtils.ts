// src/cryptoUtils.ts
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import { ec as EC } from "elliptic";
import { pemToArrayBuffer, arrayBufferToHex, stringToUint8Array } from "./utils";

const ec = new EC('secp256k1');

export const parseCertificate = (pem: string): pkijs.Certificate => {
    const buffer = pemToArrayBuffer(pem);
    const asn1 = asn1js.fromBER(buffer);
    if(asn1.offset === -1) throw new Error("Invalid Certificate PEM");
    return new pkijs.Certificate({ schema: asn1.result });
};

// Tách chuỗi PEM thành mảng Certificates (Chain)
export const parseCertificateChain = (chainPem: string): pkijs.Certificate[] => {
    const certs: pkijs.Certificate[] = [];

    // Regex tìm tất cả các block certificate
    const matches = chainPem.match(/-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----/g);

    if (matches) {
        matches.forEach(certPem => {
            try {
                const cert = parseCertificate(certPem);
                certs.push(cert);
            } catch (e) {
                console.warn("Skipping invalid cert block in chain", e);
            }
        });
    }

    return certs;
};

// Hàm lấy thông tin chi tiết để hiển thị
export const getCertificateDetails = (pem: string) => {
    const cert = parseCertificate(pem);
    let commonName = "UnknownDefault";
    let email = "email_default@gmail.com";

    // Duyệt qua Subject để tìm CN (2.5.4.3)
    for (const attr of cert.subject.typesAndValues) {
        const type = attr.type;
        // @ts-ignore
        const value = attr.value.valueBlock.value;
        if (type === "2.5.4.3") commonName = value;
        if (type === "1.2.840.113549.1.9.1") email = value;
    }
    return { commonName, email };
};

// Tính Hash của Certificate (SHA-256) cho thuộc tính ESS
export const computeCertificateHash = async (cert: pkijs.Certificate): Promise<ArrayBuffer> => {
    const certBuffer = cert.toSchema(true).toBER(false);
    return await window.crypto.subtle.digest("SHA-256", certBuffer);
};

export const getPrivateKeyHexFromPem = (pem: string): string => {
    const b64 = pem.replace(/(-----(BEGIN|END)[\w\s]+-----|\s)/g, "");
    const binaryString = window.atob(b64);
    const bytes = stringToUint8Array(binaryString);
    const asn1 = asn1js.fromBER(bytes.buffer);

    let foundKey: string | null = null;
    function searchPrivateKey(block: any) {
        if (foundKey) return;
        if (block.idBlock.tagClass === 1 && block.idBlock.tagNumber === 4) {
            const hex = arrayBufferToHex(block.valueBlock.valueHex);
            if (hex.length === 64) { foundKey = hex; return; }
            if (hex.length > 64) {
                try {
                    const inner = asn1js.fromBER(block.valueBlock.valueHex);
                    if (inner.offset !== -1) searchPrivateKey(inner.result);
                } catch(e) {}
            }
        }
        if (block.valueBlock && block.valueBlock.value && Array.isArray(block.valueBlock.value)) {
            for (const child of block.valueBlock.value) searchPrivateKey(child);
        }
    }
    searchPrivateKey(asn1.result);
    if (!foundKey) throw new Error("Could not find valid secp256k1 Private Key");
    return foundKey;
};

export const signHashWithSecp256k1 = (hash: Uint8Array, privateKeyHex: string): ArrayBuffer => {
    const keyPair = ec.keyFromPrivate(privateKeyHex, 'hex');
    const signature = keyPair.sign(hash, { canonical: true });
    return new Uint8Array(signature.toDER()).buffer;
};