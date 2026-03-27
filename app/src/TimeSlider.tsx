import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { yearFromDateStr } from './date-utils';

import './TimeSlider.css';

export interface TimeSliderProps {
  year: string;
  minYear: number;
  maxYear: number;
  isRange: boolean;
  onChange: (year: number, handle: number) => void;
}

// Square-root scale: gives more resolution near maxYear without being as extreme
// as a logarithmic scale. sliderPos = sqrt((year - minYear) / (maxYear - minYear)).
// The slider's internal range is 0..SLIDER_MAX (integers).
const SLIDER_MAX = 10000;

function yearToSlider(year: number, minYear: number, maxYear: number): number {
  const t = (year - minYear) / (maxYear - minYear);
  return Math.round((1 - Math.sqrt(1 - t)) * SLIDER_MAX);
}

function sliderToYear(pos: number, minYear: number, maxYear: number): number {
  const s = pos / SLIDER_MAX;
  const t = 1 - Math.pow(1 - s, 2);
  return Math.round(minYear + t * (maxYear - minYear));
}

function makeMarks(minYear: number, maxYear: number): Record<number, number> {
  const years = [minYear, 500, 1000, 1500, 1800, 1900, 2000, maxYear].filter(
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
  isRange,
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
