import {useDidStore} from "../../store/useDidStore.ts";

export default function DIDDocumentViewer() {
    const didDoc = useDidStore((s) => s.didDoc);

    if (!didDoc) return null;

    return (
        <div className="mt-4 p-4 bg-gray-100 rounded-xl shadow">
            <h2 className="font-bold text-lg mb-2">DID Document</h2>
            <pre className="text-sm bg-white p-4 rounded-xl overflow-x-scroll">
                {JSON.stringify(didDoc, null, 2)}
            </pre>
        </div>
    );
}