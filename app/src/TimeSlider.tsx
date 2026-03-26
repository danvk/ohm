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

  return (
    <div id="time-slider">
      <Slider
        min={minYear}
        max={maxYear}
        value={numericYear}
        onChange={(v) => onChange(v as number)}
        marks={{ [minYear]: minYear, [maxYear]: maxYear }}
        handleRender={(node, props) => (
          <div className="rc-slider-handle-wrap">
            {node}
            <span className="rc-slider-handle-label">{props.value}</span>
          </div>
        )}
      />
    </div>
  );
}
