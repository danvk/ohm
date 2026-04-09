/** The thing that sets the time. Either single or double slider. */

import { LinearTimeSlider } from './slider/LinearTimeSlider';
import { TimeRange } from './slider/TimeRange';
import { ScaledTimeSlider } from './slider/ScaledTimeSlider';
import { MAX_YEAR, MIN_YEAR } from './slider/slider-utils';

import './slider/TimeSlider.css';

export interface TimeControlProps {
  year: string;
  minYear: number;
  maxYear: number;
  isRange: boolean;
  onChange: (date: string) => void;
  onChangeRange: (minYear: number, maxYear: number) => void;
  onChangeIsRange: (isRange: boolean) => void;
}

/** Arrows pointing away from center: click to expand. */
function ExpandIcon() {
  return (
    <svg viewBox="0 0 16 28" width="16" height="28" aria-hidden="true">
      {/* Up arrowhead */}
      <polyline
        points="4,10 8,4 12,10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Down arrowhead */}
      <polyline
        points="4,18 8,24 12,18"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Arrows pointing toward center: click to collapse. */
function CollapseIcon() {
  return (
    <svg viewBox="0 0 16 28" width="16" height="28" aria-hidden="true">
      {/* Down arrowhead (pointing inward/down from top) */}
      <polyline
        points="4,5 8,11 12,5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Up arrowhead (pointing inward/up from bottom) */}
      <polyline
        points="4,23 8,17 12,23"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function TimeControl(props: TimeControlProps) {
  const { minYear, maxYear, year, isRange } = props;
  return (
    <div className={'time-control ' + (isRange ? 'dual' : 'single')}>
      <button
        className="time-mode-toggle-btn"
        title={isRange ? 'Collapse to single date' : 'Expand to date range'}
        onClick={() => props.onChangeIsRange(!isRange)}
      >
        {isRange ? <CollapseIcon /> : <ExpandIcon />}
      </button>
      <div className="time-control-sliders">
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
              minYear={MIN_YEAR}
              maxYear={MAX_YEAR}
              onChange={props.onChangeRange}
            />
          </>
        ) : (
          <ScaledTimeSlider year={year} onChange={props.onChange} />
        )}
      </div>
    </div>
  );
}
