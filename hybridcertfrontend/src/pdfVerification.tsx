import {PDFDict, PDFDocument, PDFHexString, PDFName} from 'pdf-lib';
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import { ec as EC } from "elliptic";
import {arrayBufferToHex, concatUint8Arrays, hexToUint8Array} from './utils';
import {verifySignRawWithSecp256k1} from "./cryptoUtils.ts";

export interface VerifyResult {
    isValid: boolean;
    signerSubject: string;
    signerIssuer: string;
    signingTime?: Date;
    errors: string[];
}

export const verifyPdfPAdES = async (pdfBuffer: ArrayBuffer): Promise<VerifyResult> => {
    const result: VerifyResult = {
        isValid: false,
        signerSubject: "Unknown",
        signerIssuer: "Unknown",
        errors: []
    };

    try {
        // --- 1. EXTRACT SIGNATURE FROM PDF ---
        const pdfDoc = await PDFDocument.load(pdfBuffer, {ignoreEncryption: true});
        const acroForm = pdfDoc.catalog.lookup(PDFName.of('AcroForm'));

        if (!acroForm || !(acroForm instanceof PDFDict)) throw new Error("Tài liệu chưa được ký (Document not signed)");
        const fields = acroForm.lookup(PDFName.of('Fields'));
        // @ts-ignore
        if (!fields || !fields.array || fields.array.length === 0) throw new Error("Không tìm thấy trường chữ ký");

        // @ts-ignore
        const sigWidget = pdfDoc.context.lookup(fields.array[0]) as PDFDict;
        const sigDictRef = sigWidget.lookup(PDFName.of('V')) as PDFDict;

        const contentsObj = sigDictRef.lookup(PDFName.of('Contents'));
        let signatureBytes: Uint8Array;


        if (contentsObj instanceof PDFHexString) {
            // PDFHexString.asString() trả về chuỗi hex (không có < >)
            let hex = contentsObj.asString().trim();
            if (hex.startsWith('<') && hex.endsWith('>')) hex = hex.slice(1, -1);

            // Chuyển cặp hex -> bytes
            signatureBytes = hexToUint8Array(hex);
        } else {
            throw new Error("Nội dung chữ ký không phải định dạng Hex String");
        }

        // --- 2. CLEANUP PADDING & PARSE ASN.1 ---
        // Tìm điểm kết thúc thực sự của ASN.1 Structure để loại bỏ padding 00
        // asn1js.fromBER sẽ trả về offset - vị trí kết thúc của block hợp lệ đầu tiên
        const asn1 = asn1js.fromBER(signatureBytes.buffer as ArrayBuffer);
        if (asn1.offset === -1) throw new Error("Không thể phân tích cấu trúc ASN.1 từ chữ ký");

        // Let PKIjs parse ContentInfo for us
        const contentInfo = new pkijs.ContentInfo({schema: asn1.result});

        // contentInfo.content SHOULD be the SignedData schema (maybe wrapped with [0]).
        // PKIjs expects contentInfo.content to be an asn1js object representing SignedData

        // --- 4. PARSE SIGNED DATA ---
        // Lúc này ta đã có đúng schema của SignedData, pkijs sẽ không báo lỗi nữa
        const signedData = new pkijs.SignedData({schema: contentInfo.content});

        // --- 5. EXTRACT CERTIFICATE ---
        if (!signedData.certificates || signedData.certificates.length === 0) {
            result.errors.push("Không tìm thấy chứng chỉ trong CMS.");
            return result;
        }

        const signerCert = signedData.certificates[0];

        // Lấy thông tin hiển thị
        // @ts-ignore
        result.signerSubject = signerCert.subject.typesAndValues.map(t => t.value.valueBlock.value).join(", ");
        // @ts-ignore
        result.signerIssuer = signerCert.issuer.typesAndValues.map(t => t.value.valueBlock.value).join(", ");

        // --- 6. VERIFY HASH (INTEGRITY) ---
        // @ts-ignore
        const byteRange = sigDictRef.lookup(PDFName.of('ByteRange')).asArray().map(n => n.asNumber());
        const pdfBytes = new Uint8Array(pdfBuffer);
        const range1 = pdfBytes.subarray(byteRange[0], byteRange[0] + byteRange[1]);
        const range2 = pdfBytes.subarray(byteRange[2], byteRange[2] + byteRange[3]);
        const calculatedHash = await window.crypto.subtle.digest("SHA-256", concatUint8Arrays([range1, range2]).buffer as ArrayBuffer);

        const signerInfo = signedData.signerInfos[0];
        // @ts-ignore
        const signedAttrs = signerInfo.signedAttrs;
        let embeddedHash: ArrayBuffer | null = null;

        if (signedAttrs && signedAttrs.attributes) {
            for (const attr of signedAttrs.attributes) {
                if (attr.type === "1.2.840.113549.1.9.4") embeddedHash = attr.values[0].valueBlock.valueHex;
                if (attr.type === "1.2.840.113549.1.9.5") result.signingTime = attr.values[0].toDate();
            }
        }

        if (arrayBufferToHex(calculatedHash) !== arrayBufferToHex(embeddedHash!)) {
            result.errors.push("Sai lệch giá trị băm: Tài liệu đã bị thay đổi (Hash Mismatch: Document has been modified).");
        }

        // --- 7. VERIFY CRYPTO SIGNATURE ---
        const spki = signerCert.subjectPublicKeyInfo;
        const publicKeyHex = arrayBufferToHex(spki.subjectPublicKey.valueBlock.valueHex);
        const signatureBuffer = signerInfo.signature.valueBlock.valueHex;

        // Re-hash attributes (Tag Fix 31)
        const attrsEncoder = new pkijs.SignedAndUnsignedAttributes({type: 0, attributes: signedAttrs.attributes});
        const viewAttrs = new Uint8Array(attrsEncoder.toSchema().toBER(false));
        viewAttrs[0] = 0x31;
        // const attrsHash = await window.crypto.subtle.digest("SHA-256", viewAttrs.buffer as ArrayBuffer);
        // ECDSA_verify( DER(SignedAttributes), signature )
        if (!verifySignRawWithSecp256k1(publicKeyHex, signatureBuffer, viewAttrs)) {
            result.errors.push("Chữ ký mật mã không hợp lệ (Invalid Cryptographic Signature).");
        }

        if (result.errors.length === 0) result.isValid = true;

    } catch (e: any) {
        console.error("Verification Error:", e);
        result.errors.push("Ngoại lệ trong quá trình xác minh: " + e.message);
    }
    return result;
};