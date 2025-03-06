const API_BASE_URL = process.env.REACT_APP_USE_NGINX_PROXY === 'true' ? '' : 'http://localhost:7999';
const WS_BASE_URL = process.env.REACT_APP_USE_NGINX_PROXY === 'true' ? '' : 'ws://localhost:7999';

export { API_BASE_URL, WS_BASE_URL };