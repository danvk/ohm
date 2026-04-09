import React from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr, yearToDateStr, DATE_STR_REGEX } from '../date-utils';

import './TimeSlider.css';
import {
  SLIDER_MAX,
  PIECEWISE_MAX_YEAR,
  yearToSliderPiecewise,
  sliderToYearPiecewise,
  snapYearPiecewise,
  makeHistoricalMarksPiecewise,
} from './slider-utils';

export const SQRT_MIN_YEAR = -6000;
export const SQRT_MAX_YEAR = PIECEWISE_MAX_YEAR;

const MARKS = makeHistoricalMarksPiecewise();

export interface SqrtTimeSliderProps {
  year: string;
  onChange: (date: string) => void;
}

export function SqrtTimeSlider({ year, onChange }: SqrtTimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = yearToSliderPiecewise(numericYear);
  const pct = (sliderValue / SLIDER_MAX) * 100;

  const [editing, setEditing] = React.useState(false);
  const [editValue, setEditValue] = React.useState('');

  const commitEdit = () => {
    if (DATE_STR_REGEX.test(editValue)) {
      const parsedYear = yearFromDateStr(editValue);
      if (parsedYear >= SQRT_MIN_YEAR && parsedYear <= SQRT_MAX_YEAR) {
        onChange(editValue);
      }
    }
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commitEdit();
    else if (e.key === 'Escape') setEditing(false);
  };

  const yearLabel = editing ? (
    <input
      className="rc-slider-handle-label rc-slider-label-input"
      style={{
        left: `${pct}%`,
        width: `${Math.max(4, editValue.length + 1)}ch`,
      }}
      value={editValue}
      autoFocus
      onChange={(e) => setEditValue(e.target.value)}
      onBlur={commitEdit}
      onKeyDown={handleKeyDown}
    />
  ) : (
    <span
      className="rc-slider-handle-label"
      style={{ left: `${pct}%` }}
      onDoubleClick={() => {
        setEditing(true);
        setEditValue(year);
      }}
    >
      {year}
    </span>
  );

  return (
    <div className="time-slider-sqrt">
      <div className="rc-slider-wrap">
        {yearLabel}
        <Slider
          min={0}
          max={SLIDER_MAX}
          value={sliderValue}
          styles={{
            track: { height: 8, backgroundColor: 'rgba(0,0,0,0)' },
            rail: { height: 8 },
          }}
          marks={MARKS}
          onChange={(v) => {
            const pos = v as number;
            const rawYear = sliderToYearPiecewise(pos);
            onChange(yearToDateStr(snapYearPiecewise(pos, rawYear)));
          }}
        />
      </div>
    </div>
  );
}
