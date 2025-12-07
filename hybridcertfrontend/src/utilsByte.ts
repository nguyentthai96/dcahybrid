// src/utilsByte.ts

// Chuyển ArrayBuffer thành Hex String (Uppercase)
export const arrayBufferToHex = (buffer: ArrayBuffer): string => {
    return Array.from(new Uint8Array(buffer))
        .map(b => b.toString(16).padStart(2, "0"))
        .join("")
        .toUpperCase();
};

// Chuyển String thành Uint8Array
export const stringToUint8Array = (str: string): Uint8Array => {
    const arr = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) {
        arr[i] = str.charCodeAt(i);
    }
    return arr;
};

// Nối danh sách các Uint8Array lại với nhau
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

// Tìm vị trí của mảng con trong mảng cha
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

// Chuyển Base64 PEM sang ArrayBuffer
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