import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
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
  const pct = ((numericYear - minYear) / (maxYear - minYear)) * 100;

  return (
    <div id="time-slider">
      <div className="rc-slider-wrap">
        <span className="rc-slider-handle-label" style={{ left: `${pct}%` }}>
          {numericYear}
        </span>
        <Slider
          min={minYear}
          max={maxYear}
          value={numericYear}
          onChange={(v) => onChange(v as number)}
          marks={{ 0: 0, 500: 500, 1000: 1000, 1500: 1500, 2000: 2000 }}
        />
      </div>
    </div>
  );
}
