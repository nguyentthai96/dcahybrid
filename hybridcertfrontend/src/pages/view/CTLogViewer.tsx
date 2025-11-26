import {useDidStore} from "../../store/useDidStore.ts";

export default function CTLogViewer(){
    const ctRoot = useDidStore(s => s.ctRoot)
    if(!ctRoot) return null
    return (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg shadow">
            <h3 className="font-bold">CT Log (Merkle root)</h3>
            <div className="mt-2 font-mono break-all">{ctRoot}</div>
        </div>
    )
}
