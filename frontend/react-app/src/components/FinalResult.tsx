interface Props {
  result: unknown;
  status: string;
}

export function FinalResult({ result, status }: Props) {
  if (status !== "completed" || result == null) {
    return null;
  }

  return (
    <section className="panel final">
      <h2>Final Result</h2>
      <pre className="result">{typeof result === "string" ? result : JSON.stringify(result, null, 2)}</pre>
    </section>
  );
}
