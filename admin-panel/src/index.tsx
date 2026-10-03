import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { laadThema } from './thema';

laadThema();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
