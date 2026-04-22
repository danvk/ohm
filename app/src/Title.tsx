import React from 'react';

import Logo from './ohm_logo.svg';

export const Title = React.memo(({ isWhm }: { isWhm: boolean }) => {
  return !isWhm ? (
    <div className="title">
      <img src={Logo} width={30} height={30} className="logo" />
      <h3>Boundary Viewer</h3>
      <a href="https://github.com/danvk/ohm/tree/main/app" target="_blank">
        About
      </a>
    </div>
  ) : (
    <div className="title">
      <h3>WHM Boundary Viewer</h3>
      <div className="about">
        Source:{' '}
        <a href="http://www.worldhistorymaps.com/timeline.html" target="_blank">
          WorldHistoryMaps.com
        </a>
      </div>
    </div>
  );
});
