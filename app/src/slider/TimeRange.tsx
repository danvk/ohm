import { useEffect, useRef } from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';

import './TimeSlider.css';
import {
  SLIDER_MAX,
  yearToSlider,
  sliderToYear,
  snapYear,
  snapYearByPixels,
  makeHistoricalMarks,
} from './slider-utils';

export interface TimeRangeProps {
  years: [number, number];
  minYear: number;
  maxYear: number;
  onChange: (a: number, b: number) => void;
}

function Connector({ side, pct }: { side: 'left' | 'right'; pct: number }) {
  return (
    <div
      className={`rc-slider-connector rc-slider-connector-${side}`}
      style={side === 'left' ? { width: `${pct}%` } : { left: `${pct}%` }}
    >
      <div className="rc-slider-connector-v-bottom" />
      <div className="rc-slider-connector-h" />
      <div className="rc-slider-connector-v-top" />
    </div>
  );
}

export function TimeRange({
  years,
  minYear,
  maxYear,
  onChange,
}: TimeRangeProps) {
  const sliderValues = years.map((y) => yearToSlider(y, minYear, maxYear));
  const pcts = sliderValues.map((v) => (v / SLIDER_MAX) * 100);

  const wrapRef = useRef<HTMLDivElement>(null);
  // Refs so drag handler always has current values without re-registering listeners.
  const yearsRef = useRef(years);
  yearsRef.current = years;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;

    type DragState = {
      startX: number;
      startSliderA: number;
      yearWidth: number;
    };
    let drag: DragState | null = null;

    // Use capture phase so we intercept before rc-slider's own mousedown handler.
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Match track elements (rc-slider uses "rc-slider-track" or "rc-slider-track-1").
      if (!target.className.includes('rc-slider-track')) return;

      e.stopPropagation(); // Prevent rc-slider from starting its own drag.
      e.preventDefault();

      const currentYears = yearsRef.current;
      drag = {
        startX: e.clientX,
        startSliderA: yearToSlider(currentYears[0], minYear, maxYear),
        yearWidth: currentYears[1] - currentYears[0],
      };
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!drag) return;
      const sliderEl = wrap.querySelector('.rc-slider') as HTMLElement | null;
      if (!sliderEl) return;
      const rect = sliderEl.getBoundingClientRect();
      const dx = e.clientX - drag.startX;
      const deltaSlider = Math.round((dx / rect.width) * SLIDER_MAX);
      const newSliderA = Math.max(
        0,
        Math.min(SLIDER_MAX, drag.startSliderA + deltaSlider),
      );
      const newYearA = sliderToYear(newSliderA, minYear, maxYear);
      const clampedA = Math.max(
        minYear,
        Math.min(newYearA, maxYear - drag.yearWidth),
      );
      const snappedA = snapYearByPixels(clampedA, rect.width, minYear, maxYear);
      onChangeRef.current(snappedA, snappedA + drag.yearWidth);
    };

    const onMouseUp = () => {
      drag = null;
    };

    wrap.addEventListener('mousedown', onMouseDown, true);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    return () => {
      wrap.removeEventListener('mousedown', onMouseDown, true);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [minYear, maxYear]);

  return (
    <div className="time-slider-range">
      <div className="rc-slider-wrap" ref={wrapRef}>
        <Connector side="left" pct={pcts[0]} />
        <Connector side="right" pct={pcts[1]} />
        <Slider
          min={0}
          max={SLIDER_MAX}
          value={sliderValues}
          range={{ draggableTrack: false }}
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
              snapYear(v1, sliderToYear(v1, minYear, maxYear), minYear, maxYear),
              snapYear(v2, sliderToYear(v2, minYear, maxYear), minYear, maxYear),
            );
          }}
          marks={makeHistoricalMarks(minYear, maxYear)}
        />
      </div>
    </div>
  );
}
