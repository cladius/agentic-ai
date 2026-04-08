import React from 'react';
import { createRoot } from 'react-dom/client';
import PlaygroundApp from './App';
import FrontendApp from './frontend/App';

const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);

//Determine which app to render
const isPlayground = window.location.pathname.includes('playground');
root.render(
  isPlayground ? <PlaygroundApp /> : <FrontendApp />
);