import React from 'react';
import { yearFromDateStr } from './date-utils';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  onChange: (year: number) => void;
}

export function TimeSlider({
  year,
  minYear,
  maxYear,
  onChange,
}: TimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const thumbFraction = (numericYear - minYear) / (maxYear - minYear);

  return (
    <div id="time-slider">
      <div id="time-slider-track-row">
        <div
          id="time-slider-input-wrap"
          style={{ '--thumb-fraction': thumbFraction } as React.CSSProperties}
        >
          <span id="year-display">{year}</span>
          <input
            id="year"
            type="range"
            min={minYear}
            max={maxYear}
            value={numericYear}
            onChange={(e) => onChange(e.currentTarget.valueAsNumber)}
          />
        </div>
        <span className="time-slider-label time-slider-label-min">
          {minYear}
        </span>
        <span className="time-slider-label time-slider-label-max">
          {maxYear}
        </span>
      </div>
    </div>
  );
}
