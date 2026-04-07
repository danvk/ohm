/** The thing that sets the time. Either single or double slider. */

import React from 'react';
import { LinearTimeSlider } from './LinearTimeSlider';
import { TimeRange } from './TimeRange';

import './TimeSlider.css';

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
  const { minYear, maxYear, year } = props;
  return (
    <div className="time-control">
      <LinearTimeSlider
        minYear={minYear}
        maxYear={maxYear}
        year={year}
        onChange={props.onChange}
      />
      <TimeRange
        years={[minYear, maxYear]}
        minYear={-4000}
        maxYear={2030}
        onChange={props.onChangeRange}
      />
    </div>
  );
}
