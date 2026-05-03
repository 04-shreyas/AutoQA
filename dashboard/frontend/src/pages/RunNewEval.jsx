import RunForm from '../components/RunForm';

export default function RunNewEval() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-violet-300">Run evaluation</p>
          <h1 className="text-3xl font-semibold text-white">Run new QA pipeline</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Submit a prompt and translate model responses into fresh QA test coverage.
          </p>
        </div>
      </header>

      <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
        <RunForm />
      </div>
    </div>
  );
}
