import { useEffect, useRef, useState } from 'react';
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

// Height above the range rc-slider-wrap top that the linear slider handle sits at.
// (measured: linear handle center is 29px above the range wrap top)
const TOP_OVERHANG = 29;
// How far below the range wrap top the range handle center sits.
// (measured: range handle center is 9px below the range wrap top)
const BOTTOM_OVERHANG = 9;

function ConnectorSvg({ side, pct }: { side: 'left' | 'right'; pct: number }) {
  const H = TOP_OVERHANG + BOTTOM_OVERHANG; // total height in px
  const midY = H / 2;
  // Corner radius for the two bends (in px). Adjust to taste.
  const R = Math.min(midY, 8);

  const svgRef = useRef<SVGSVGElement>(null);
  const [W, setW] = useState(0);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const obs = new ResizeObserver(() => setW(el.getBoundingClientRect().width));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Path description:
  // For 'left': handle is bottom-right (W, H), label edge is top-left (0, 0).
  //   Down from handle: M W H → vertical up to midY on right side (with rounded corner)
  //   Horizontal left across middle
  //   Vertical up to top-left (with rounded corner)
  //
  // Using SVG arc commands for the rounded corners:
  //   arc syntax: A rx ry x-rotation large-arc-flag sweep-flag x y

  let d = '';
  if (W > 0) {
    if (side === 'left') {
      // Start: bottom-right (handle)
      // End: top-left (label edge)
      // Path: up from (W, H) → bend → left → bend → up to (0, 0)
      d = [
        `M ${W} ${H}`,
        `L ${W} ${midY + R}`,
        `A ${R} ${R} 0 0 0 ${W - R} ${midY}`,
        `L ${R} ${midY}`,
        `A ${R} ${R} 0 0 1 0 ${midY - R}`,
        `L 0 0`,
      ].join(' ');
    } else {
      // Start: bottom-left (handle)
      // End: top-right (label edge)
      d = [
        `M 0 ${H}`,
        `L 0 ${midY + R}`,
        `A ${R} ${R} 0 0 1 ${R} ${midY}`,
        `L ${W - R} ${midY}`,
        `A ${R} ${R} 0 0 0 ${W} ${midY - R}`,
        `L ${W} 0`,
      ].join(' ');
    }
  }

  return (
    <svg
      ref={svgRef}
      className={`rc-slider-connector rc-slider-connector-${side}`}
      style={side === 'left' ? { width: `${pct}%` } : { left: `${pct}%` }}
    >
      <path d={d} />
    </svg>
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

  return (
    <div className="time-slider-range">
      <div className="rc-slider-wrap">
        <ConnectorSvg side="left" pct={pcts[0]} />
        <ConnectorSvg side="right" pct={pcts[1]} />
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
