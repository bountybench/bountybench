import React from "react";
import { createRoot } from "react-dom/client";
import 'react-toastify/dist/ReactToastify.css';
import App from './App';
import './index.css';

const rootElement = document.getElementById("root");
const root = createRoot(rootElement);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);