import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from './date-utils';

import './TimeSlider.css';

export const SQRT_MIN_YEAR = -6000;
export const SQRT_MAX_YEAR = 2030;

const SLIDER_MAX = 10000;
const SNAP_THRESHOLD = 60;

function yearToSlider(year: number): number {
  const t = (year - SQRT_MIN_YEAR) / (SQRT_MAX_YEAR - SQRT_MIN_YEAR);
  return Math.round((1 - Math.sqrt(1 - t)) * SLIDER_MAX);
}

function sliderToYear(pos: number): number {
  const s = pos / SLIDER_MAX;
  const t = 1 - Math.pow(1 - s, 2);
  return Math.round(SQRT_MIN_YEAR + t * (SQRT_MAX_YEAR - SQRT_MIN_YEAR));
}

function snapYear(sliderPos: number, year: number): number {
  const nearest = Math.round(year / 50) * 50;
  const nearestSliderPos = yearToSlider(nearest);
  if (Math.abs(sliderPos - nearestSliderPos) <= SNAP_THRESHOLD) {
    return nearest;
  }
  if (year < 1900) {
    return Math.round(year / 10) * 10;
  }
  return year;
}

function makeMarks(): Record<number, number> {
  const years = [
    SQRT_MIN_YEAR,
    -4000,
    -3000,
    -2000,
    -1000,
    0,
    500,
    1000,
    1500,
    1800,
    1900,
    2000,
    SQRT_MAX_YEAR,
  ];
  return Object.fromEntries(years.map((y) => [yearToSlider(y), y]));
}

const MARKS = makeMarks();

export interface SqrtTimeSliderProps {
  year: string;
  onChange: (year: number) => void;
}

export function SqrtTimeSlider({ year, onChange }: SqrtTimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = yearToSlider(numericYear);
  const pct = (sliderValue / SLIDER_MAX) * 100;

  return (
    <div className="time-slider-sqrt">
      <div className="rc-slider-wrap">
        <span className="rc-slider-handle-label" style={{ left: `${pct}%` }}>
          {numericYear}
        </span>
        <Slider
          min={0}
          max={SLIDER_MAX}
          value={sliderValue}
          styles={{
            track: { height: 8, backgroundColor: 'rgba(0,0,0,0)' },
            rail: { height: 8, backgroundColor: 'var(--slider-color)' },
          }}
          marks={MARKS}
          onChange={(v) => {
            const pos = v as number;
            const rawYear = sliderToYear(pos);
            onChange(snapYear(pos, rawYear));
          }}
        />
      </div>
    </div>
  );
}
