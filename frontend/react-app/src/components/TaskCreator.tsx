import { useState } from "react";

interface Props {
  onSubmit: (input: string) => void;
  disabled: boolean;
  skill: string | null;
  onClearSkill: () => void;
}

export function TaskCreator({ onSubmit, disabled, skill, onClearSkill }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  };

  return (
    <div className="creator">
      {skill && (
        <span className="creator-skill">
          技能: <span className="mono">{skill}</span>
          <button className="creator-skill-clear" onClick={onClearSkill} title="取消选中">
            ×
          </button>
        </span>
      )}
      <input
        className="input"
        type="text"
        placeholder="输入任务,例如:查询支付网关的服务状态"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSubmit();
        }}
      />
      <button className="button" onClick={handleSubmit} disabled={disabled || !value.trim()}>
        {disabled ? "执行中..." : "发送"}
      </button>
    </div>
  );
}
