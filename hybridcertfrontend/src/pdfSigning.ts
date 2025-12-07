// src/pdfSigning.ts
import { PDFDocument, PDFName, PDFNumber, PDFHexString, PDFString, PDFDict, PDFArray } from 'pdf-lib';
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import { parseCertificate, getPrivateKeyHexFromPem, signHashWithSecp256k1 } from './cryptoUtils';
import { concatUint8Arrays, findSubarrayIndex, stringToUint8Array, arrayBufferToHex } from './utilsByte';

export const signPdfPAdES = async (
    pdfBuffer: ArrayBuffer,
    privateKeyPem: string,
    userCertPem: string,
    caCertPem?: string,
): Promise<Uint8Array> => {

    // -----------------------------------------------------------
    // 1. CHUẨN BỊ FILE PDF VÀ TẠO PLACEHOLDER
    // -----------------------------------------------------------
    const pdfDoc = await PDFDocument.load(pdfBuffer);
    const pages = pdfDoc.getPages();

    // Dùng số lớn làm placeholder để dành chỗ trống dài
    const byteRangePlaceholder = [
        PDFNumber.of(0),
        PDFNumber.of(9999999999),
        PDFNumber.of(9999999999),
        PDFNumber.of(9999999999),
    ];

    // 8KB placeholder cho chữ ký
    const SIGNATURE_LENGTH = 8192;
    const signatureHexPlaceholder = "0".repeat(SIGNATURE_LENGTH);

    const signatureDictRef = pdfDoc.context.register(
        pdfDoc.context.obj({
            Type: 'Sig',
            Filter: 'Adobe.PPKLite',
            SubFilter: 'adbe.pkcs7.detached',
            ByteRange: byteRangePlaceholder,
            Contents: PDFHexString.of(signatureHexPlaceholder),
            Reason: PDFString.of('Digitally Signed by React Client'),
            M: PDFString.fromDate(new Date()),
        }),
    );

    const widgetDictRef = pdfDoc.context.register(
        pdfDoc.context.obj({
            Type: 'Annot',
            Subtype: 'Widget',
            FT: 'Sig',
            Rect: [0, 0, 0, 0],
            V: signatureDictRef,
            P: pages[0].ref,
            F: 4,
        }),
    );

    pages[0].node.set(PDFName.of('Annots'), pdfDoc.context.obj([widgetDictRef]));

    const acroForm = pdfDoc.catalog.lookup(PDFName.of('AcroForm'));
    if (!acroForm || !(acroForm instanceof PDFDict)) {
        pdfDoc.catalog.set(PDFName.of('AcroForm'), pdfDoc.context.obj({
            Fields: [widgetDictRef],
            SigFlags: 3,
        }));
    } else {
        const fields = acroForm.lookup(PDFName.of('Fields'));
        if (fields instanceof PDFArray) {
            fields.push(widgetDictRef);
        } else {
            acroForm.set(PDFName.of('Fields'), pdfDoc.context.obj([widgetDictRef]));
        }
    }

    // Save PDF với placeholder
    // Buffer này đang chứa: /ByteRange [ 0 999... ] và Contents <000...>
    let pdfBytes = await pdfDoc.save({ useObjectStreams: false });

    // -----------------------------------------------------------
    // 2. TÍNH TOÁN VÀ GHI ĐÈ BYTERANGE *TRƯỚC* KHI HASH
    // -----------------------------------------------------------

    // Tìm vị trí chữ ký
    const signatureTag = stringToUint8Array(`<${signatureHexPlaceholder}>`);
    const startIndex = findSubarrayIndex(pdfBytes, signatureTag);

    if (startIndex === -1) throw new Error("Could not find signature placeholder.");

    const endIndex = startIndex + signatureTag.length;

    // Tính ByteRange thực tế
    const actualByteRange = [
        0,
        startIndex,
        endIndex,
        pdfBytes.length - endIndex
    ];

    // Tạo chuỗi ByteRange mới
    const newByteRangeStr = `/ByteRange [${actualByteRange.join(' ')}]`;

    // Tìm và thay thế placeholder ByteRange TRONG BUFFER
    // Điều này đảm bảo Hash sẽ tính trên giá trị ByteRange ĐÚNG
    const pdfString = new TextDecoder("latin1").decode(pdfBytes);
    const byteRangePlaceholderRegex = /\/ByteRange\s*\[\s*0\s+9999999999\s+9999999999\s+9999999999\s*\]/;
    const match = pdfString.match(byteRangePlaceholderRegex);

    if (!match || match.index === undefined) {
        throw new Error("Could not find ByteRange placeholder.");
    }

    const placeholderStr = match[0];
    if (newByteRangeStr.length > placeholderStr.length) {
        throw new Error("ByteRange string exceeded placeholder length.");
    }

    // Pad khoảng trắng cho bằng độ dài cũ
    const paddedByteRangeStr = newByteRangeStr.padEnd(placeholderStr.length, " ");
    const byteRangeBytes = stringToUint8Array(paddedByteRangeStr);

    // GHI ĐÈ TRỰC TIẾP VÀO BUFFER GỐC
    pdfBytes.set(byteRangeBytes, match.index);

    // -----------------------------------------------------------
    // 3. TÍNH HASH (Lúc này buffer đã có ByteRange đúng)
    // -----------------------------------------------------------

    const range1 = pdfBytes.subarray(0, startIndex);
    const range2 = pdfBytes.subarray(endIndex);
    const dataToSign = concatUint8Arrays([range1, range2]);

    const pdfHashBuffer = await window.crypto.subtle.digest("SHA-256", dataToSign.buffer as ArrayBuffer);

    // -----------------------------------------------------------
    // 4. TẠO CMS (PKCS#7)
    // -----------------------------------------------------------
    const userCert = parseCertificate(userCertPem);
    const certificates = [userCert];
    if (caCertPem) certificates.push(parseCertificate(caCertPem));

    const signerInfo = new pkijs.SignerInfo({
        version: 1,
        sid: new pkijs.IssuerAndSerialNumber({
            issuer: userCert.issuer,
            serialNumber: userCert.serialNumber,
        }),
        digestAlgorithm: new pkijs.AlgorithmIdentifier({
            algorithmId: "2.16.840.1.101.3.4.2.1", // SHA-256
            algorithmParams: new asn1js.Null(),
        }),
        signatureAlgorithm: new pkijs.AlgorithmIdentifier({
            algorithmId: "1.2.840.10045.4.3.2", // ecdsa-with-SHA256
            // QUAN TRỌNG: Params cho ECDSA signature phải ABSENT (không để Null)
        }),
    });

    const signedAttrs = new pkijs.SignedAndUnsignedAttributes({
        type: 0,
        attributes: [
            new pkijs.Attribute({
                type: "1.2.840.113549.1.9.3", // ContentType
                values: [new asn1js.ObjectIdentifier({ value: "1.2.840.113549.1.7.1" })]
            }),
            new pkijs.Attribute({
                type: "1.2.840.113549.1.9.4", // MessageDigest
                values: [new asn1js.OctetString({ valueHex: pdfHashBuffer })]
            }),
            new pkijs.Attribute({
                type: "1.2.840.113549.1.9.5", // SigningTime
                values: [new asn1js.UTCTime({ valueDate: new Date() })]
            })
        ]
    });

    // @ts-ignore
    signerInfo.signedAttrs = signedAttrs;

    // Hash Attributes (Fix Tag 0xA0 -> 0x31)
    const encodedAttrs = signedAttrs.toSchema().toBER(false);
    const viewAttrs = new Uint8Array(encodedAttrs);
    viewAttrs[0] = 0x31; // SET OF tag

    const attrsHash = await window.crypto.subtle.digest("SHA-256", viewAttrs.buffer as ArrayBuffer);

    // Ký Hash bằng Elliptic secp256k1
    const privateKeyHex = getPrivateKeyHexFromPem(privateKeyPem);
    const signatureValue = signHashWithSecp256k1(new Uint8Array(attrsHash), privateKeyHex);

    signerInfo.signature = new asn1js.OctetString({ valueHex: signatureValue });

    const signedData = new pkijs.SignedData({
        version: 1,
        encapContentInfo: new pkijs.EncapsulatedContentInfo({
            eContentType: "1.2.840.113549.1.7.1",
        }),
        certificates: certificates,
        signerInfos: [signerInfo],
    });

    const cmsContent = signedData.toSchema().toBER(false);
    const cmsHex = arrayBufferToHex(cmsContent);
    const paddedHex = cmsHex.padEnd(signatureHexPlaceholder.length, '0');

    // -----------------------------------------------------------
    // 5. INJECT CHỮ KÝ (ByteRange đã update ở bước 2 rồi)
    // -----------------------------------------------------------

    const signatureBlock = stringToUint8Array(`<${paddedHex}>`);

    // Ghép file cuối cùng
    const finalPdfBytes = concatUint8Arrays([
        range1,
        signatureBlock,
        range2
    ]);

    return finalPdfBytes;
};