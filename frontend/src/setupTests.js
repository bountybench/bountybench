// setupTests.js

// Silence console.log
global.console.log = jest.fn();

// Silence console.error
global.console.error = jest.fn();

// setupTests.js
global.TextEncoder = require('util').TextEncoder;
global.TextDecoder = require('util').TextDecoder;