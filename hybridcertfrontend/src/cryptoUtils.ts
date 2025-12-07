// src/cryptoUtils.ts
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import { ec as EC } from "elliptic";
import { pemToArrayBuffer, arrayBufferToHex, stringToUint8Array } from "./utilsByte";

// Khởi tạo Curve secp256k1
const ec = new EC('secp256k1');

// Parse Certificate X509
export const parseCertificate = (pem: string): pkijs.Certificate => {
    const buffer = pemToArrayBuffer(pem);
    const asn1 = asn1js.fromBER(buffer);
    if(asn1.offset === -1) throw new Error("Invalid Certificate PEM");
    return new pkijs.Certificate({ schema: asn1.result });
};

/**
 * Tìm Private Key (32 bytes) trong cấu trúc ASN.1 PEM.
 * Sửa lỗi Crash và hỗ trợ PKCS#8 lồng nhau.
 */
export const getPrivateKeyHexFromPem = (pem: string): string => {
    // 1. Decode PEM -> Binary -> ASN.1
    const b64 = pem.replace(/(-----(BEGIN|END)[\w\s]+-----|\s)/g, "");
    const binaryString = window.atob(b64);
    const bytes = stringToUint8Array(binaryString);
    const asn1 = asn1js.fromBER(bytes.buffer);

    if (asn1.offset === -1) throw new Error("Error parsing ASN.1 from Private Key PEM");

    let foundKey: string | null = null;

    // Hàm đệ quy duyệt cây ASN.1
    function searchPrivateKey(block: any) {
        if (foundKey) return;

        // --- FIX LỖI CRASH Ở ĐÂY ---
        // Kiểm tra block tồn tại và có idBlock hợp lệ trước khi truy cập tagClass
        if (!block || !block.idBlock) return;

        // Check Tag 0x04 (OctetString)
        if (block.idBlock.tagClass === 1 && block.idBlock.tagNumber === 4) {
            const hex = arrayBufferToHex(block.valueBlock.valueHex);

            // Trường hợp 1: Tìm thấy trực tiếp key 32 bytes (64 hex chars)
            if (hex.length === 64) {
                foundKey = hex;
                return;
            }

            // Trường hợp 2: PKCS#8 Wrapper
            // Private Key thực sự thường nằm trong một OctetString lớn hơn (wrapper).
            // Nếu OctetString này > 32 bytes, ta thử parse nội dung bên trong nó xem có phải là cấu trúc ASN.1 lồng nhau không.
            if (hex.length > 64) {
                try {
                    // Thử parse content của OctetString như một ASN.1 mới
                    const innerAsn1 = asn1js.fromBER(block.valueBlock.valueHex);
                    if (innerAsn1.offset !== -1 && innerAsn1.result) {
                        // Nếu parse thành công, đệ quy vào trong cấu trúc vừa tìm được
                        searchPrivateKey(innerAsn1.result);
                    }
                } catch (e) {
                    // Không phải ASN.1 structure, bỏ qua
                }
            }
        }

        // Duyệt các con (Children)
        if (block.valueBlock && block.valueBlock.value && Array.isArray(block.valueBlock.value)) {
            for (const child of block.valueBlock.value) {
                searchPrivateKey(child);
            }
        }
    }

    searchPrivateKey(asn1.result);

    if (!foundKey) {
        throw new Error("Could not find a valid 32-byte Private Key (secp256k1) in the provided PEM.");
    }

    return foundKey;
};

/**
 * Ký Hash bằng Elliptic Curve (secp256k1)
 * Trả về định dạng DER (ASN.1) cho PDF
 */
export const signHashWithSecp256k1 = (hash: Uint8Array, privateKeyHex: string): ArrayBuffer => {
    const keyPair = ec.keyFromPrivate(privateKeyHex, 'hex');

    // Yêu cầu thư viện elliptic ký hash
    // canonical: true để đảm bảo chữ ký "s" value thấp (chuẩn Bitcoin/Ethereum, tương thích tốt PAdES)
    const signature = keyPair.sign(hash, { canonical: true });

    // Convert sang DER format (ASN.1)
    const derSign = signature.toDER();
    return new Uint8Array(derSign).buffer;
};