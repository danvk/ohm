import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';

import './TimeSlider.css';

export interface TimeRangeProps {
  years: [number, number];
  minYear: number;
  maxYear: number;
  onChange: (a: number, b: number) => void;
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

export function TimeRange({
  years,
  minYear,
  maxYear,
  onChange,
}: TimeRangeProps) {
  const sliderValues = years.map((y) => yearToSlider(y, minYear, maxYear));

  return (
    <div className="time-slider-range">
      <div className="rc-slider-wrap">
        <Slider
          min={0}
          max={SLIDER_MAX}
          value={sliderValues}
          range
          styles={{
            track: { height: 8 },
            rail: { height: 8 },
          }}
          onChange={(vs) => {
            if (!Array.isArray(vs)) {
              throw new Error('blah');
            }
            const [v1, v2] = vs;
            onChange(
              sliderToYear(v1, minYear, maxYear),
              sliderToYear(v2, minYear, maxYear),
            );
          }}
          marks={makeMarks(minYear, maxYear)}
        />
      </div>
    </div>
  );
}
