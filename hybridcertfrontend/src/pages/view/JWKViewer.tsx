import { useDidStore } from "../../store/useDidStore.ts";

export default function JWKViewer() {
    const jwk = useDidStore((s) => s.jwk);

    if (!jwk) return null;

    return (
        <div className="mt-4 bg-gray-100 p-4 rounded-xl shadow">
            <h2 className="font-bold text-lg mb-2">Public Key (JWK)</h2>
            <pre className="text-sm bg-white p-4 rounded-xl overflow-x-scroll">
                {JSON.stringify(jwk, null, 2)}
            </pre>
        </div>
    );
}
