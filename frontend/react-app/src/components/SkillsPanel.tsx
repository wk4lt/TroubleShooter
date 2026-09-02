import { useEffect, useState } from "react";
import { listSkills } from "../api";
import { SkillMeta } from "../types";

interface Props {
  selected: string | null;
  onSelect: (name: string | null) => void;
}

export function SkillsPanel({ selected, onSelect }: Props) {
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSkills()
      .then(setSkills)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const toggle = (name: string) => {
    onSelect(selected === name ? null : name);
  };

  return (
    <section className="panel skills-panel">
      <h2>技能</h2>
      {error && <div className="file-error">{error}</div>}
      {skills.length === 0 && !error && <div className="empty">暂无技能</div>}
      <ul className="skill-list">
        {skills.map((s) => (
          <li
            key={s.name}
            className={`skill-item ${selected === s.name ? "skill-item-selected" : ""}`}
            onClick={() => toggle(s.name)}
            title="点击选中该技能"
          >
            <span className="skill-name mono">{s.name}</span>
            <span className="skill-desc">{s.description}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
