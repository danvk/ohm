import React from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { ticks } from 'd3-array';
import { yearFromDateStr, yearToDateStr, DATE_STR_REGEX } from '../date-utils';

import './TimeSlider.css';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  onChange: (date: string) => void;
  onChangeMinYear?: (year: number) => void;
  onChangeMaxYear?: (year: number) => void;
}

type EditingField = 'min' | 'max' | 'year' | null;

export function LinearTimeSlider({
  year,
  minYear,
  maxYear,
  onChange,
  onChangeMinYear,
  onChangeMaxYear,
}: TimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = (numericYear - minYear) / (maxYear - minYear);
  const pct = sliderValue * 100;
  const tickMarks = Object.fromEntries(
    ticks(minYear, maxYear, 5).map((y) => [y, ' ']),
  );

  const [editing, setEditing] = React.useState<EditingField>(null);
  const [editValue, setEditValue] = React.useState('');

  const startEdit = (field: EditingField, value: string | number) => {
    setEditing(field);
    setEditValue(String(value));
  };

  const commitEdit = () => {
    if (editing === 'year') {
      if (DATE_STR_REGEX.test(editValue)) {
        onChange(editValue);
      }
    } else {
      const parsed = parseInt(editValue, 10);
      if (!isNaN(parsed)) {
        if (editing === 'min') onChangeMinYear?.(parsed);
        else if (editing === 'max') onChangeMaxYear?.(parsed);
      }
    }
    setEditing(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commitEdit();
    else if (e.key === 'Escape') setEditing(null);
  };

  const renderBoundLabel = (field: 'min' | 'max', value: number) => {
    const className = `rc-slider-range-label rc-slider-range-label-${field === 'min' ? 'left' : 'right'}`;
    if (editing === field) {
      return (
        <input
          className={`${className} rc-slider-label-input`}
          value={editValue}
          style={{ width: `${Math.max(4, editValue.length + 1)}ch` }}
          autoFocus
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
        />
      );
    }
    return (
      <span className={className} onDoubleClick={() => startEdit(field, value)}>
        {value}
      </span>
    );
  };

  const renderYearLabel = () => {
    if (editing === 'year') {
      return (
        <input
          className="rc-slider-handle-label rc-slider-label-input"
          style={{ left: `${pct}%`, width: `${Math.max(4, editValue.length + 1)}ch` }}
          value={editValue}
          autoFocus
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
        />
      );
    }
    return (
      <span
        className="rc-slider-handle-label"
        style={{ left: `${pct}%` }}
        onDoubleClick={() => startEdit('year', year)}
      >
        {year}
      </span>
    );
  };

  return (
    <div className="time-slider-linear">
      {renderBoundLabel('min', minYear)}
      <div className="rc-slider-wrap">
        {renderYearLabel()}
        <Slider
          min={minYear}
          max={maxYear}
          value={numericYear}
          styles={{
            track: { height: 8 },
            rail: { height: 8 },
          }}
          marks={tickMarks}
          onChange={(v) => onChange(yearToDateStr(v as number))}
        />
      </div>
      {renderBoundLabel('max', maxYear)}
    </div>
  );
}
