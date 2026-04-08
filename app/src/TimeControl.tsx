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

/** Schematic icon: single slider with a thumb and label above it (Date mode). */
function DateIcon() {
  return (
    <svg viewBox="0 0 28 22" width="28" height="22" aria-hidden="true">
      {/* Rail */}
      <line x1="2" y1="16" x2="26" y2="16" stroke="currentColor" strokeOpacity="0.4" strokeWidth="2" strokeLinecap="round" />
      {/* Thumb */}
      <circle cx="18" cy="16" r="3.5" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.25" />
      {/* Tick from rail to label */}
      <line x1="18" y1="6" x2="18" y2="11" stroke="currentColor" strokeOpacity="0.7" strokeWidth="1.5" strokeLinecap="round" />
      {/* Year label bubble */}
      <rect x="12" y="2" width="12" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.2" fill="currentColor" fillOpacity="0.15" />
    </svg>
  );
}

/** Schematic icon: two-slider range with bracket connectors to upper bar (Range mode). */
function RangeIcon() {
  const lx = 7;    // left thumb x
  const rx = 21;   // right thumb x
  const topY = 5;  // upper bar y
  const midY = 13; // connector horizontal y
  const botY = 20; // lower rail y
  return (
    <svg viewBox="0 0 28 24" width="28" height="24" aria-hidden="true">
      {/* Upper bar (LinearTimeSlider rail) */}
      <line x1="2" y1={topY} x2="26" y2={topY} stroke="currentColor" strokeOpacity="0.4" strokeWidth="2" strokeLinecap="round" />
      {/* Left bracket: vertical down */}
      <line x1={lx} y1={topY} x2={lx} y2={botY} stroke="currentColor" strokeOpacity="0.7" strokeWidth="1.5" strokeLinecap="round" />
      {/* Right bracket: vertical down */}
      <line x1={rx} y1={topY} x2={rx} y2={botY} stroke="currentColor" strokeOpacity="0.7" strokeWidth="1.5" strokeLinecap="round" />
      {/* Horizontal connector mid-bracket */}
      <line x1={lx} y1={midY} x2={rx} y2={midY} stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.5" strokeLinecap="round" />
      {/* Lower rail */}
      <line x1="2" y1={botY} x2="26" y2={botY} stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" strokeLinecap="round" />
      {/* Selected track segment */}
      <line x1={lx} y1={botY} x2={rx} y2={botY} stroke="currentColor" strokeOpacity="0.7" strokeWidth="2.5" strokeLinecap="round" />
      {/* Left thumb */}
      <circle cx={lx} cy={botY} r="3" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.25" />
      {/* Right thumb */}
      <circle cx={rx} cy={botY} r="3" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.25" />
    </svg>
  );
}

export function TimeControl(props: TimeControlProps) {
  const { minYear, maxYear, year, isRange } = props;
  return (
    <div className="time-control">
      <div className="time-mode-toggle-v">
        <button
          className={`time-mode-toggle-btn${!isRange ? ' active' : ''}`}
          title="Single date"
          onClick={() => props.onChangeIsRange(false)}
        >
          <DateIcon />
        </button>
        <button
          className={`time-mode-toggle-btn${isRange ? ' active' : ''}`}
          title="Date range"
          onClick={() => props.onChangeIsRange(true)}
        >
          <RangeIcon />
        </button>
      </div>
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
              minYear={-6000}
              maxYear={2030}
              onChange={props.onChangeRange}
            />
          </>
        ) : (
          <SqrtTimeSlider year={year} onChange={props.onChange} />
        )}
      </div>
    </div>
  );
}
