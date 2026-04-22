import React from 'react';

function goToOhm() {
  const search = '' + window.location.search;
  window.open(`https://danvk.org/ohm/${search}`, '_blank');
}

export function OhmLink() {
  return (
    <div className="ohm-link">
      <a href="#" onClick={goToOhm}>
        View OHM
      </a>
    </div>
  );
}
