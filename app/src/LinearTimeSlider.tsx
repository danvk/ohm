import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from './date-utils';

import './TimeSlider.css';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  onChange: (year: number) => void;
}

export function LinearTimeSlider({
  year,
  minYear,
  maxYear,
  onChange,
}: TimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = (numericYear - minYear) / (maxYear - minYear);
  const pct = sliderValue * 100;

  return (
    <div className="time-slider-linear">
      <div className="rc-slider-wrap">
        <span className="rc-slider-handle-label" style={{ left: `${pct}%` }}>
          {numericYear}
        </span>
        <Slider
          min={minYear}
          max={maxYear}
          value={numericYear}
          styles={{
            track: { height: 8 },
            rail: { height: 8 },
          }}
          onChange={(v) => onChange(v as number)}
        />
      </div>
    </div>
  );
}
