import {PDFDict, PDFDocument, PDFHexString, PDFName} from 'pdf-lib';
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import {ec as EC} from "elliptic";
import {arrayBufferToHex, concatUint8Arrays} from './utils';

const ec = new EC('secp256k1');

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
        const pdfDoc = await PDFDocument.load(pdfBuffer, {ignoreEncryption: true});

        const acroForm = pdfDoc.catalog.lookup(PDFName.of('AcroForm'));
        if (!acroForm || !(acroForm instanceof PDFDict)) throw new Error("Document not signed");

        const fields = acroForm.lookup(PDFName.of('Fields'));
        // @ts-ignore
        if (!fields || !fields.array || fields.array.length === 0) throw new Error("No signature fields");

        // @ts-ignore
        const sigWidget = pdfDoc.context.lookup(fields.array[0]) as PDFDict;
        const sigDictRef = sigWidget.lookup(PDFName.of('V')) as PDFDict;

        // Get Contents Bytes
        const contentsObj = sigDictRef.lookup(PDFName.of('Contents'));
        let signatureBytes: Uint8Array;
        if (contentsObj instanceof PDFHexString) {
            const binaryStr = contentsObj.asString();
            signatureBytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) signatureBytes[i] = binaryStr.charCodeAt(i);
        } else {
            throw new Error("Signature Contents is not a HexString.");
        }

        let actualLength = signatureBytes.length;
        while (actualLength > 0 && signatureBytes[actualLength - 1] === 0) {
            actualLength--;
        }
        const validBytes = signatureBytes.subarray(0, actualLength);

        console.log("Verify Crypto Parse ASN.1 from buffer (Auto ignore padding)");

        // Parse ASN.1 from buffer (Auto ignore padding)
        const asn1 = asn1js.fromBER(validBytes.buffer as ArrayBuffer);
        if (asn1.offset === -1) throw new Error("Cannot parse ASN.1 from signature.");

        console.log("Verify Crypto Parse ASN.1 from buffer (Auto ignore padding)", asn1);

        let signedData: pkijs.SignedData;

        // --- TRY PARSE CONTENT INFO FIRST ---
        try {
            const contentInfo = new pkijs.ContentInfo({ schema: asn1.result });
            // Lấy SignedData từ ContentInfo.content
            signedData = new pkijs.SignedData({ schema: contentInfo.content });
        } catch (e) {
            // Fallback: Nếu không phải ContentInfo, thử parse trực tiếp SignedData (Hỗ trợ file cũ)
            // console.warn("ContentInfo parse failed, trying direct SignedData...");
            try {
                signedData = new pkijs.SignedData({ schema: asn1.result });
            } catch (err2) {
                throw new Error("Invalid CMS Structure: Neither ContentInfo nor SignedData.");
            }
        }

        if (!signedData.certificates || signedData.certificates.length === 0) {
            result.errors.push("No certificates found in CMS.");
            return result;
        }

        const signerCert = signedData.certificates[0];
        console.log("Verify Crypto signerCert ", signerCert);
        result.signerSubject = signerCert.subject.typesAndValues.map(t => t.value.valueBlock.value).join(", ");
        // @ts-ignore
        result.signerIssuer = signerCert.issuer.typesAndValues.map(t => t.value.valueBlock.value).join(", ");

        // Verify Hash
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
            result.errors.push("Hash Mismatch.");
        }

        // Verify Crypto
        const spki = signerCert.subjectPublicKeyInfo;
        const publicKeyHex = arrayBufferToHex(spki.subjectPublicKey.valueBlock.valueHex);
        const keyPair = ec.keyFromPublic(publicKeyHex, 'hex');
        const signatureBuffer = signerInfo.signature.valueBlock.valueHex;

        const attrsEncoder = new pkijs.SignedAndUnsignedAttributes({type: 0, attributes: signedAttrs.attributes});
        const viewAttrs = new Uint8Array(attrsEncoder.toSchema().toBER(false));
        viewAttrs[0] = 0x31;
        const attrsHash = await window.crypto.subtle.digest("SHA-256", viewAttrs.buffer as ArrayBuffer);

        if (!keyPair.verify(new Uint8Array(attrsHash), new Uint8Array(signatureBuffer))) {
            result.errors.push("Invalid Cryptographic Signature.");
        }

        if (result.errors.length === 0) result.isValid = true;

    } catch (e: any) {
        console.error("Error verify:", e);
        result.errors.push("Error verify: " + e.message);
    }
    return result;
};