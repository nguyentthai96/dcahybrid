// src/utils.ts

export const arrayBufferToHex = (buffer: ArrayBuffer): string => {
    return Array.from(new Uint8Array(buffer))
        .map(b => b.toString(16).padStart(2, "0"))
        .join("")
        .toUpperCase();
};

export const hexToUint8Array = (hexString: string): Uint8Array => {
    if (hexString.length % 2 !== 0) throw new Error("Invalid hex string");
    const array = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < hexString.length; i += 2) {
        array[i / 2] = parseInt(hexString.substr(i, 2), 16);
    }
    return array;
};

export const stringToUint8Array = (str: string): Uint8Array => {
    const arr = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) {
        arr[i] = str.charCodeAt(i);
    }
    return arr;
};

export const concatUint8Arrays = (arrays: Uint8Array[]): Uint8Array => {
    const totalLength = arrays.reduce((acc, curr) => acc + curr.length, 0);
    const result = new Uint8Array(totalLength);
    let offset = 0;
    for (const arr of arrays) {
        result.set(arr, offset);
        offset += arr.length;
    }
    return result;
};

export const findSubarrayIndex = (haystack: Uint8Array, needle: Uint8Array): number => {
    const haystackLen = haystack.length;
    const needleLen = needle.length;
    for (let i = 0; i <= haystackLen - needleLen; i++) {
        let match = true;
        for (let j = 0; j < needleLen; j++) {
            if (haystack[i + j] !== needle[j]) {
                match = false;
                break;
            }
        }
        if (match) return i;
    }
    return -1;
};

export const pemToArrayBuffer = (pem: string): ArrayBuffer => {
    const b64Lines = pem.replace(/(-----(BEGIN|END)[\w\s]+-----|\s)/g, "");
    const str = window.atob(b64Lines);
    const buf = new ArrayBuffer(str.length);
    const view = new Uint8Array(buf);
    for (let i = 0; i < str.length; i++) {
        view[i] = str.charCodeAt(i);
    }
    return buf;
};

// Hàm quan trọng để hiển thị tên có dấu trên Okular/Adobe
export const stringToUtf16Hex = (str: string): string => {
    let hex = "";
    for (let i = 0; i < str.length; i++) {
        const code = str.charCodeAt(i);
        hex += code.toString(16).padStart(4, "0");
    }
    // FEFF là Byte Order Mark (BOM) báo hiệu UTF-16BE
    return "FEFF" + hex.toUpperCase();
};