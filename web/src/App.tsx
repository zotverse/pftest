import { useState } from 'react';
import { Terminal, CheckCircle, XCircle } from 'lucide-react';

export default function App() {
  const [text, setText] = useState('');
  const [status, setStatus] = useState<'IDLE' | 'PROCESSING' | 'DONE'>('IDLE');
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setStatus('PROCESSING');
    setResult(null);
    try {
      const res = await fetch('http://localhost:8000/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ founder_id: 'user_v1', text }),
      });
      const data = await res.json();
      console.log("API Response:", data); // Debug log
      setResult(data);
      setStatus('DONE');
    } catch (e) {
      console.error(e);
      setStatus('IDLE');
      alert('System Offline. Check Python Console.');
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-2xl mx-auto">
      <header className="mb-12 border-b border-green-900 pb-4">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Terminal className="w-6 h-6" /> PURF ENGINE v1
        </h1>
      </header>

      <div className="space-y-6">
        <div>
          <label className="block text-xs uppercase tracking-widest text-green-700 mb-2">
            Submission
          </label>
          <textarea
            className="w-full h-40 bg-black border border-green-800 p-4 text-sm focus:border-green-500 outline-none text-green-100 placeholder:text-green-900/50"
            placeholder="Describe your startup. Be precise. (e.g. 'I help Dentists save $5k/yr...')"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={status === 'PROCESSING'}
          />
        </div>

        {status === 'IDLE' && (
          <button
            onClick={handleSubmit}
            className="w-full bg-green-900/30 border border-green-600 text-green-400 py-3 uppercase tracking-widest hover:bg-green-900/50 transition-colors"
          >
            Submit to Tribunal
          </button>
        )}

        {status === 'PROCESSING' && (
          <div className="text-center text-xs animate-pulse text-green-500 py-8 border border-green-900/30">
            /// EXTRACTING CLAIMS...
            <br />
            /// RUNNING CAUSAL INVARIANTS...
          </div>
        )}

        {status === 'DONE' && result && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* VERDICT BANNER */}
            <div className={`p-6 border-l-4 mb-8 ${
              result.verdict?.verdict === 'PASS' 
                ? 'border-green-500 bg-green-900/10' 
                : 'border-red-500 bg-red-900/10'
            }`}>
              <div className="flex items-center gap-4 mb-2">
                {result.verdict?.verdict === 'PASS' ? (
                  <CheckCircle className="w-8 h-8 text-green-500" />
                ) : (
                  <XCircle className="w-8 h-8 text-red-500" />
                )}
                <h2 className={`text-4xl font-black tracking-tighter ${
                   result.verdict?.verdict === 'PASS' ? 'text-green-500' : 'text-red-500'
                }`}>
                  {result.verdict?.verdict || "ERROR"}
                </h2>
              </div>
              
              {result.verdict?.verdict === 'ERROR' ? (
                 <p className="text-red-400 font-mono mt-4 text-sm">
                    SYSTEM ERROR: {result.verdict.reason}
                 </p>
              ) : (
                 <p className="text-xs font-mono opacity-50 pl-12">
                   MERKLE: {result.verdict?.merkle_root}
                 </p>
              )}
            </div>

            {/* TRACE LOG */}
            {result.verdict?.trace && (
                <div className="space-y-2">
                  <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-4">Rule Trace</h3>
                  {result.verdict.trace.map((r: any, i: number) => (
                    <div key={i} className={`p-3 border ${
                      r.passed ? 'border-green-900/30 text-green-700' : 'border-red-900 text-red-500'
                    }`}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-xs">{r.rule_id}</span>
                        <span className="text-[10px]">{r.passed ? 'PASS' : 'FAIL'}</span>
                      </div>
                      <p className="text-sm font-mono">{r.reason}</p>
                    </div>
                  ))}
                </div>
            )}

            {/* EXTRACTED DATA DEBUG */}
            <div className="mt-8 border-t border-green-900 pt-8 opacity-50">
               <h3 className="text-xs uppercase tracking-widest mb-4">Clerk Extraction</h3>
               <pre className="text-[10px] whitespace-pre-wrap font-mono text-green-800">
                 {JSON.stringify(result.claims, null, 2)}
               </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
