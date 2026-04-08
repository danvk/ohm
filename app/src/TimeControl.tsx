/** The thing that sets the time. Either single or double slider. */

import { LinearTimeSlider } from './slider/LinearTimeSlider';
import { TimeRange } from './slider/TimeRange';
import { SqrtTimeSlider } from './slider/SqrtTimeSlider';

import './slider/TimeSlider.css';

export interface TimeControlProps {
  year: string;
  minYear: number;
  maxYear: number;
  isRange: boolean;
  onChange: (year: number) => void;
  onChangeRange: (minYear: number, maxYear: number) => void;
  onChangeIsRange: (isRange: boolean) => void;
}

export function TimeControl(props: TimeControlProps) {
  const { minYear, maxYear, year, isRange } = props;
  return (
    <div className="time-control">
      <button
        className="time-mode-toggle"
        title={isRange ? 'Switch to single-date mode' : 'Switch to date-range mode'}
        onClick={() => props.onChangeIsRange(!isRange)}
      >
        {isRange ? '⇔' : '▸'}
      </button>
      {isRange ? (
        <>
          <LinearTimeSlider
            minYear={minYear}
            maxYear={maxYear}
            year={year}
            onChange={props.onChange}
            onChangeMinYear={(newMin) => props.onChangeRange(newMin, maxYear)}
            onChangeMaxYear={(newMax) => props.onChangeRange(minYear, newMax)}
          />
          <TimeRange
            years={[minYear, maxYear]}
            minYear={-6000}
            maxYear={2030}
            onChange={props.onChangeRange}
          />
        </>
      ) : (
        <SqrtTimeSlider year={year} onChange={props.onChange} />
      )}
    </div>
  );
}
