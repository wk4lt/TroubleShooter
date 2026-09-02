import { useCallback, useEffect, useRef, useState } from "react";
import { deleteFile, fileDownloadUrl, listFiles, uploadFile } from "../api";
import { log } from "../logger";
import { FileMeta } from "../types";

interface Props {
  status: string;
}

interface PendingFile {
  file: File;
  relpath: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function readAllEntries(reader: any): Promise<any[]> {
  return new Promise((resolve) => {
    const entries: any[] = [];
    const read = () => {
      reader.readEntries((batch: any[]) => {
        if (batch.length === 0) {
          resolve(entries);
        } else {
          entries.push(...batch);
          read();
        }
      }, () => resolve(entries));
    };
    read();
  });
}

async function traverseEntry(entry: any, base: string): Promise<PendingFile[]> {
  if (entry.isFile) {
    const file: File = await new Promise((resolve, reject) =>
      entry.file(resolve, reject)
    );
    const relpath = base ? `${base}/${file.name}` : file.name;
    return [{ file, relpath }];
  }
  if (entry.isDirectory) {
    const children = await readAllEntries(entry.createReader());
    const nested = base ? `${base}/${entry.name}` : entry.name;
    const results: PendingFile[] = [];
    for (const child of children) {
      results.push(...(await traverseEntry(child, nested)));
    }
    return results;
  }
  return [];
}

export function FilePanel({ status }: Props) {
  const [files, setFiles] = useState<FileMeta[]>([]);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dirInputRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    try {
      setFiles(await listFiles());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (status === "completed") reload();
  }, [status, reload]);

  useEffect(() => {
    const timer = setInterval(reload, 5000);
    return () => clearInterval(timer);
  }, [reload]);

  const uploadMany = useCallback(
    async (pending: PendingFile[]) => {
      if (pending.length === 0) return;
      setError(null);
      try {
        for (const p of pending) {
          await uploadFile(p.file, p.relpath);
          log("info", `上传文件 ${p.relpath} (${p.file.size}B)`);
        }
        await reload();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        log("error", `上传文件失败: ${e}`);
      }
    },
    [reload]
  );

  const handleFiles = useCallback(
    async (list: FileList | null) => {
      if (!list || list.length === 0) return;
      const pending = Array.from(list).map((f) => ({
        file: f,
        relpath: f.webkitRelativePath || f.name,
      }));
      await uploadMany(pending);
    },
    [uploadMany]
  );

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const items = e.dataTransfer.items;
      if (items && items.length > 0) {
        const pending: PendingFile[] = [];
        for (let i = 0; i < items.length; i++) {
          const entry = (items[i] as any).webkitGetAsEntry?.();
          if (entry) {
            pending.push(...(await traverseEntry(entry, "")));
          }
        }
        if (pending.length > 0) {
          await uploadMany(pending);
          return;
        }
      }
      await handleFiles(e.dataTransfer.files);
    },
    [uploadMany, handleFiles]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteFile(id);
      log("info", `删除文件 ${id}`);
      await reload();
    },
    [reload]
  );

  return (
    <section className="panel file-panel">
      <div className="file-panel-head">
        <h2>文件</h2>
        <button className="ghost-btn" onClick={reload} title="刷新">
          ↻
        </button>
      </div>

      <div
        className={`dropzone ${dragging ? "dropzone-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="dropzone-text" onClick={() => inputRef.current?.click()}>
          拖拽文件或文件夹到这里
        </div>
        <div className="dropzone-actions">
          <button
            className="ghost-btn"
            onClick={() => inputRef.current?.click()}
          >
            选择文件
          </button>
          <button
            className="ghost-btn"
            onClick={() => dirInputRef.current?.click()}
          >
            选择文件夹
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <input
          ref={dirInputRef}
          type="file"
          hidden
          {...({ webkitdirectory: "" } as any)}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && <div className="file-error">{error}</div>}

      <ul className="file-list">
        {files.length === 0 && <li className="file-empty">暂无文件</li>}
        {files.map((f) => (
          <li key={f.file_id} className="file-item">
            <span className="file-name" title={f.relpath || f.filename}>
              {f.relpath || f.filename}
            </span>
            <span className="file-size">{formatSize(f.size)}</span>
            <a className="file-action" href={fileDownloadUrl(f.file_id)} download={f.filename}>
              ↓
            </a>
            <button className="file-action" onClick={() => handleDelete(f.file_id)} title="删除">
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
