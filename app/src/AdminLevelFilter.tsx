import React from 'react';

export interface AdminLevelFilterProps {
  adminLevels: Set<string>;
  onChange: (adminLevels: Set<string>) => void;
}

// const LEVELS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'] as const;
const LEVELS = ['2'] as const;

export function AdminLevelFilter({
  adminLevels,
  onChange,
}: AdminLevelFilterProps) {
  const handleChange = (level: string, checked: boolean) => {
    const next = new Set(adminLevels);
    if (checked) {
      next.add(level);
    } else {
      next.delete(level);
    }
    onChange(next);
  };

  return (
    <div className="admin-level-filter">
      <span className="admin-level-filter-label">admin_level=</span>
      {LEVELS.map((level) => (
        <label key={level} className="admin-level-filter-item">
          <input
            type="checkbox"
            checked={adminLevels.has(level)}
            onChange={(e) => handleChange(level, e.target.checked)}
          />
          {level}
        </label>
      ))}
    </div>
  );
}
