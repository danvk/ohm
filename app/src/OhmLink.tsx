import React from 'react';

function goToOhm(e: React.MouseEvent) {
  e.preventDefault();
  const search = window.location.search;
  window.open(`https://danvk.org/ohm/${search}`, '_blank');
}

export function OhmLink() {
  return (
    <div className="ohm-link">
      <a href="https://danvk.org/ohm/" onClick={goToOhm}>
        View OHM
      </a>
    </div>
  );
}
