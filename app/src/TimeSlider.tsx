import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from './date-utils';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  onChange: (year: number) => void;
}

// Logarithmic scale: each century closer to maxYear gets CENTURY_RATIO× the slider
// width of the preceding century. The base is CENTURY_RATIO^((maxYear-minYear)/100).
// The slider's internal range is 0..SLIDER_MAX (integers).
const SLIDER_MAX = 10000;
const CENTURY_RATIO = 1.5; // each century gets 1.5× the width of the one before it
const LOG_BASE = Math.pow(CENTURY_RATIO, 20); // for a 0–2000 range (20 centuries)

function yearToSlider(year: number, minYear: number, maxYear: number): number {
  const range = maxYear - minYear;
  const t = (year - minYear) / range;
  return Math.round(
    ((Math.pow(LOG_BASE, t) - 1) / (LOG_BASE - 1)) * SLIDER_MAX,
  );
}

function sliderToYear(pos: number, minYear: number, maxYear: number): number {
  const t =
    Math.log(1 + (pos / SLIDER_MAX) * (LOG_BASE - 1)) / Math.log(LOG_BASE);
  return Math.round(minYear + t * (maxYear - minYear));
}

function makeMarks(minYear: number, maxYear: number): Record<number, number> {
  const years = [minYear, 500, 1000, 1500, 1800, 1900, 1950, maxYear].filter(
    (y) => y >= minYear && y <= maxYear,
  );
  return Object.fromEntries(
    years.map((y) => [yearToSlider(y, minYear, maxYear), y]),
  );
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
          onChange={(v) =>
            onChange(sliderToYear(v as number, minYear, maxYear))
          }
          marks={makeMarks(minYear, maxYear)}
        />
      </div>
    </div>
  );
}
