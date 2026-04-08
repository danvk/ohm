import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from '../date-utils';

import './TimeSlider.css';
import {
  SLIDER_MAX,
  yearToSlider,
  sliderToYear,
  snapYear,
  makeHistoricalMarks,
} from './slider-utils';

export const SQRT_MIN_YEAR = -6000;
export const SQRT_MAX_YEAR = 2030;

const MARKS = makeHistoricalMarks(SQRT_MIN_YEAR, SQRT_MAX_YEAR);

export interface SqrtTimeSliderProps {
  year: string;
  onChange: (year: number) => void;
}

export function SqrtTimeSlider({ year, onChange }: SqrtTimeSliderProps) {
  const numericYear = yearFromDateStr(year);
  const sliderValue = yearToSlider(numericYear, SQRT_MIN_YEAR, SQRT_MAX_YEAR);
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
            const rawYear = sliderToYear(pos, SQRT_MIN_YEAR, SQRT_MAX_YEAR);
            onChange(snapYear(pos, rawYear, SQRT_MIN_YEAR, SQRT_MAX_YEAR));
          }}
        />
      </div>
    </div>
  );
}
