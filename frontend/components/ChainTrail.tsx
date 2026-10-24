"use client";

export default function ChainTrail({
  hash,
  network,
  labels,
}: {
  hash: string;
  network: string;
  labels: { title: string; prev: string; yours: string; next: string };
}) {
  const shortHash = hash ? `${hash.slice(0, 10)}…${hash.slice(-6)}` : "—";
  const blocks = [
    { label: labels.prev, value: "···", accent: false },
    { label: labels.yours, value: shortHash, accent: true },
    { label: labels.next, value: "···", accent: false },
  ];

  return (
    <section aria-label={labels.title}>
      <h3 className="text-sm font-medium text-muted">
        {labels.title} · <span className="tabular-nums">{network}</span>
      </h3>
      <div className="mt-2 flex items-stretch gap-0">
        {blocks.map((block, i) => (
          <div key={block.label} className="flex min-w-0 flex-1 items-center">
            {i > 0 && <span className="h-px w-4 shrink-0 bg-line" aria-hidden="true" />}
            <div
              className={
                "min-w-0 flex-1 rounded-lg border px-2 py-2 text-center" +
                (block.accent ? " border-accent" : " border-line")
              }
            >
              <p
                className={
                  "truncate font-mono text-[11px] " +
                  (block.accent ? "text-accent" : "text-muted")
                }
              >
                {block.value}
              </p>
              <p className="mt-0.5 truncate text-[11px] text-muted">{block.label}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
