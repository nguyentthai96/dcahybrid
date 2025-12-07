// src/pdfSigning.ts
import {
    PDFDocument, PDFName, PDFNumber, PDFHexString, PDFString,
    PDFDict, PDFArray, StandardFonts
} from 'pdf-lib';
import * as pkijs from "pkijs";
import * as asn1js from "asn1js";
import {
    parseCertificate, getPrivateKeyHexFromPem, signHashWithSecp256k1,
    getCertificateDetails, computeCertificateHash, parseCertificateChain
} from './cryptoUtils';
import {
    concatUint8Arrays, findSubarrayIndex, stringToUint8Array,
    arrayBufferToHex, stringToUtf16Hex
} from './utils';


export const signPdfPAdES = async (
    pdfBuffer: ArrayBuffer,
    privateKeyPem: string,
    userCertPem: string,
    caCertPem?: string,
): Promise<Uint8Array> => {

    // 1. CHUẨN BỊ PDF
    const pdfDoc = await PDFDocument.load(pdfBuffer);
    const pages = pdfDoc.getPages();
    const firstPage = pages[0];

    const certDetails = getCertificateDetails(userCertPem);
    const signerName = certDetails.commonName || "Default Unknown Signer";

    // --- 2. TẠO VISUAL SIGNATURE ---
    const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const resources = pdfDoc.context.obj({ Font: { Helv: font.ref } });

    // Normalize tên để hiển thị trên trang (ASCII only để tránh lỗi font Helvetica)
    const displayName = signerName.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const appearanceStream = pdfDoc.context.register(
        pdfDoc.context.flateStream(
            `q 0.95 0.95 0.95 rg 0 0 250 50 re f 0.5 G 0.5 w 0 0 250 50 re S Q ` +
            `BT /Helv 10 Tf 0 g 10 35 Td (Digitally Signed by:) Tj ` +
            `0 -12 Td (${displayName}) Tj ` +
            `0 -12 Td (${new Date().toLocaleString()}) Tj ET`,
            {
                Type: 'XObject', Subtype: 'Form', FormType: 1,
                BBox: [0, 0, 250, 50], Resources: resources
            }
        )
    );

    // 3. DICTIONARY
    // Tăng size lên 20KB để chắc chắn chứa đủ ContentInfo + Chain
    const byteRangePlaceholder = [PDFNumber.of(0), PDFNumber.of(9999999999), PDFNumber.of(9999999999), PDFNumber.of(9999999999)];
    const SIGNATURE_LENGTH = 20480;
    const signatureHexPlaceholder = "0".repeat(SIGNATURE_LENGTH);

    // Convert các chuỗi sang UTF-16BE Hex để Okular hiển thị tiếng Việt
    const nameHex = stringToUtf16Hex(signerName);
    const reasonHex = stringToUtf16Hex("Digitally Signed by PAdES-B");
    const locationHex = stringToUtf16Hex("Vietnam");

    const signatureDictRef = pdfDoc.context.register(
        pdfDoc.context.obj({
            Type: 'Sig',
            // Dùng ETSI.CAdES.detached để Okular biết đây là PAdES chuẩn
            Filter: 'Adobe.PPKLite',
            SubFilter: 'ETSI.CAdES.detached', // Chuẩn PAdES cho Okular
            ByteRange: byteRangePlaceholder,
            Contents: PDFHexString.of(signatureHexPlaceholder),
            // Thời gian ký
            M: PDFString.fromDate(new Date()),

            // Các trường thông tin hiển thị trong Panel
            Name: PDFHexString.of(nameHex),         // Hiện tên "Signed by..."
            Reason: PDFHexString.of(reasonHex),     // Hiện lý do
            Location: PDFHexString.of(locationHex), // Hiện địa điểm
            ContactInfo: PDFString.of(certDetails.email || ""),

            // Prop_Build giúp Viewer nhận diện tool tạo (Optional)
           //    Prop_Build: pdfDoc.context.obj({
           //        Filter: pdfDoc.context.obj({ Name: PDFName.of('Adobe.PPKLite') }),
           //        App: pdfDoc.context.obj({ Name: PDFName.of('ReactPDFSigner') })
           //    })
        }),
    );

    const widgetDictRef = pdfDoc.context.register(
        pdfDoc.context.obj({
            Type: 'Annot', Subtype: 'Widget', FT: 'Sig',
            Rect: [50, 50, 300, 100],
            V: signatureDictRef, P: firstPage.ref, F: 4,
            AP: pdfDoc.context.obj({ N: appearanceStream }),
        }),
    );

    firstPage.node.set(PDFName.of('Annots'), pdfDoc.context.obj([widgetDictRef]));

    const acroForm = pdfDoc.catalog.lookup(PDFName.of('AcroForm'));
    if (!acroForm || !(acroForm instanceof PDFDict)) {
        pdfDoc.catalog.set(PDFName.of('AcroForm'), pdfDoc.context.obj({ Fields: [widgetDictRef], SigFlags: 3 }));
    } else {
        const fields = acroForm.lookup(PDFName.of('Fields'));
        if (fields instanceof PDFArray) fields.push(widgetDictRef);
        else acroForm.set(PDFName.of('Fields'), pdfDoc.context.obj([widgetDictRef]));
    }

    let pdfBytes = await pdfDoc.save({ useObjectStreams: false });

    // --- 4. UPDATE BYTERANGE ---
    const signatureTag = stringToUint8Array(`<${signatureHexPlaceholder}>`);
    const startIndex = findSubarrayIndex(pdfBytes, signatureTag);
    if (startIndex === -1) throw new Error("Signature placeholder not found");
    const endIndex = startIndex + signatureTag.length;

    const actualByteRange = [0, startIndex, endIndex, pdfBytes.length - endIndex];
    const newByteRangeStr = `/ByteRange [${actualByteRange.join(' ')}]`;

    const pdfString = new TextDecoder("latin1").decode(pdfBytes);
    const byteRangeRegex = /\/ByteRange\s*\[\s*0\s+9999999999\s+9999999999\s+9999999999\s*\]/;
    const match = pdfString.match(byteRangeRegex);
    if (!match || match.index === undefined) throw new Error("ByteRange placeholder not found");

    const paddedByteRangeStr = newByteRangeStr.padEnd(match[0].length, " ");
    pdfBytes.set(stringToUint8Array(paddedByteRangeStr), match.index);

    // 5. TẠO CMS (FIX NÚT VIEW CERTIFICATE)
    const range1 = pdfBytes.subarray(0, startIndex);
    const range2 = pdfBytes.subarray(endIndex);
    const dataToSign = concatUint8Arrays([range1, range2]);
    const pdfHashBuffer = await window.crypto.subtle.digest("SHA-256", dataToSign.buffer as ArrayBuffer);

    // Certs & Chain
    const userCert = parseCertificate(userCertPem);
    // Khởi tạo mảng certificates với User Cert
    const certificates: pkijs.Certificate[] = [userCert];

    // Nếu có CA Chain (Intermediate/Root), parse và thêm vào mảng
    if (caCertPem && caCertPem.trim().length > 0) {
        const chainCerts = parseCertificateChain(caCertPem);
        // Spread operator để đẩy toàn bộ chain vào mảng chung
        certificates.push(...chainCerts);
    }

    // --- TẠO ATTRIBUTES (Giữ nguyên logic SigningCertificateV2) ---
    const certHash = await computeCertificateHash(userCert);


    const ESSCertIDv2 = new asn1js.Sequence({
        value: [
            new asn1js.Sequence({ value: [ new asn1js.ObjectIdentifier({ value: "2.16.840.1.101.3.4.2.1" }) ] }),
            new asn1js.OctetString({ valueHex: certHash })
        ]
    });
    const SigningCertificateV2 = new asn1js.Sequence({
        value: [ new asn1js.Sequence({ value: [ESSCertIDv2] }) ]
    });
    const signingCertV2Attr = new pkijs.Attribute({
        type: "1.2.840.113549.1.9.16.2.47",
        values: [SigningCertificateV2]
    });

    // SignerInfo
    const signerInfo = new pkijs.SignerInfo({
        version: 1,
        sid: new pkijs.IssuerAndSerialNumber({ issuer: userCert.issuer, serialNumber: userCert.serialNumber }),
        digestAlgorithm: new pkijs.AlgorithmIdentifier({ algorithmId: "2.16.840.1.101.3.4.2.1", algorithmParams: new asn1js.Null() }),
        signatureAlgorithm: new pkijs.AlgorithmIdentifier({ algorithmId: "1.2.840.10045.4.3.2" }) // Params ABSENT
    });

    // Signed Attributes
    const signedAttrs = new pkijs.SignedAndUnsignedAttributes({
        type: 0,
        attributes: [
            new pkijs.Attribute({ type: "1.2.840.113549.1.9.3", values: [new asn1js.ObjectIdentifier({ value: "1.2.840.113549.1.7.1" })] }),
            new pkijs.Attribute({ type: "1.2.840.113549.1.9.4", values: [new asn1js.OctetString({ valueHex: pdfHashBuffer })] }),
            new pkijs.Attribute({ type: "1.2.840.113549.1.9.5", values: [new asn1js.UTCTime({ valueDate: new Date() })] }),
            signingCertV2Attr
        ]
    });

    // @ts-ignore
    signerInfo.signedAttrs = signedAttrs;

    // Hash & Sign
    const encodedAttrs = signedAttrs.toSchema().toBER(false);
    const viewAttrs = new Uint8Array(encodedAttrs);
    viewAttrs[0] = 0x31;
    const attrsHash = await window.crypto.subtle.digest("SHA-256", viewAttrs.buffer as ArrayBuffer);
    const privateKeyHex = getPrivateKeyHexFromPem(privateKeyPem);
    const signatureValue = signHashWithSecp256k1(new Uint8Array(attrsHash), privateKeyHex);
    signerInfo.signature = new asn1js.OctetString({ valueHex: signatureValue });

    // --- TẠO SIGNED DATA ---
    const signedData = new pkijs.SignedData({
        version: 3, // Version 3 hỗ trợ các extension mới tốt hơn
        encapContentInfo: new pkijs.EncapsulatedContentInfo({ eContentType: "1.2.840.113549.1.7.1" }),
        certificates: certificates, // Nhúng Full Chain
        signerInfos: [signerInfo],
    });

    // PAdES yêu cầu cấu trúc đầy đủ: ContentInfo chứa SignedData
    const contentInfo = new pkijs.ContentInfo({
        contentType: "1.2.840.113549.1.7.2", // OID cho id-signedData
        content: signedData.toSchema()
    });
    // Serialize ContentInfo (thay vì chỉ SignedData)
    const cmsContent = contentInfo.toSchema().toBER(false);
    // old not ContentInfo const cmsHex = arrayBufferToHex(signedData.toSchema().toBER(false));
    const cmsHex = arrayBufferToHex(cmsContent);



    // Inject
    if (cmsHex.length > signatureHexPlaceholder.length) throw new Error(`Signature too large (${cmsHex.length}). Increase size.`);
    const paddedHex = cmsHex.padEnd(signatureHexPlaceholder.length, '0');
    const signatureBlock = stringToUint8Array(`<${paddedHex}>`);

    return concatUint8Arrays([range1, signatureBlock, range2]);
};