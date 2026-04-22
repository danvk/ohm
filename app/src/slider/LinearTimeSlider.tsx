import React from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { ticks } from 'd3-array';
import {
  yearFromDateStr,
  yearToDateStr,
  dateStrToMonths,
  monthsToDateStr,
  DATE_STR_REGEX,
} from '../date-utils';

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

// Threshold below which month-level precision is used on the linear slider.
const MONTH_PRECISION_THRESHOLD = 20;

export function LinearTimeSlider({
  year,
  minYear,
  maxYear,
  onChange,
  onChangeMinYear,
  onChangeMaxYear,
}: TimeSliderProps) {
  const yearRange = maxYear - minYear || 1;
  const useMonths = yearRange <= MONTH_PRECISION_THRESHOLD;

  const sliderMin = useMonths ? minYear * 12 : minYear;
  const sliderMax = useMonths ? maxYear * 12 : maxYear;
  const sliderValue = useMonths ? dateStrToMonths(year) : yearFromDateStr(year);
  const sliderRange = sliderMax - sliderMin || 1;
  const pct = ((sliderValue - sliderMin) / sliderRange) * 100;

  const tickMarks = Object.fromEntries(
    ticks(minYear, maxYear, 5).map((y) => [useMonths ? y * 12 : y, ' ']),
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
          min={sliderMin}
          max={sliderMax}
          value={sliderValue}
          styles={{
            track: { height: 8 },
            rail: { height: 8 },
          }}
          marks={tickMarks}
          onChange={(v) => {
            const val = v as number;
            onChange(useMonths ? monthsToDateStr(val) : yearToDateStr(val));
          }}
        />
      </div>
      {renderBoundLabel('max', maxYear)}
    </div>
  );
}
