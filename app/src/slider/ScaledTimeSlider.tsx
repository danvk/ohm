import React from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr, yearToDateStr, DATE_STR_REGEX } from '../date-utils';

import './TimeSlider.css';
import {
  SLIDER_MAX,
  MAX_YEAR,
  yearToSlider,
  sliderToYear,
  snapYear,
  makeHistoricalMarks,
  MIN_YEAR,
} from './slider-utils';

const MARKS = makeHistoricalMarks();

export interface ScaledTimeSliderProps {
  year: string;
  onChange: (date: string) => void;
}

export function ScaledTimeSlider({ year, onChange }: ScaledTimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = yearToSlider(numericYear);
  const pct = (sliderValue / SLIDER_MAX) * 100;

  const [editing, setEditing] = React.useState(false);
  const [editValue, setEditValue] = React.useState('');

  const commitEdit = () => {
    if (DATE_STR_REGEX.test(editValue)) {
      const parsedYear = yearFromDateStr(editValue);
      if (parsedYear >= MIN_YEAR && parsedYear <= MAX_YEAR) {
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
            const rawYear = sliderToYear(pos);
            onChange(yearToDateStr(snapYear(pos, rawYear)));
          }}
        />
      </div>
    </div>
  );
}
