import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from '../date-utils';

import './TimeSlider.css';
import { SLIDER_MAX, yearToSlider, sliderToYear } from './slider-utils';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  onChange: (year: number, handle: number) => void;
}

function makeMarks(minYear: number, maxYear: number): Record<number, number> {
  const years = [minYear, 500, 1000, 1500, 1800, 1900, 2000, maxYear].filter(
    (y) => y >= minYear && y <= maxYear,
  );
  return Object.fromEntries(years.map((y) => [yearToSlider(y, minYear, maxYear), y]));
}

export function TimeSlider({
  year,
  minYear,
  maxYear,
  onChange,
}: TimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = yearToSlider(numericYear, minYear, maxYear);
  const pct = (sliderValue / SLIDER_MAX) * 100;

  return (
    <div id="time-slider">
      <div className="rc-slider-wrap">
        <span className="rc-slider-handle-label" style={{ left: `${pct}%` }}>
          {numericYear}
        </span>
        <Slider
          min={0}
          max={SLIDER_MAX}
          value={sliderValue}
          styles={{
            track: { height: 8 },
            rail: { height: 8 },
          }}
          onChange={(v) =>
            onChange(sliderToYear(v as number, minYear, maxYear), 0)
          }
          marks={makeMarks(minYear, maxYear)}
        />
      </div>
    </div>
  );
}
