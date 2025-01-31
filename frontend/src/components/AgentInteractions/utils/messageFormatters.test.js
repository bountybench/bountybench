 // messageFormatters.test.js
 import { formatData } from './messageFormatters';

 test('returns empty string for null or undefined', () => {
   expect(formatData(null)).toBe('');
   expect(formatData(undefined)).toBe('');
 });
 
 test('returns string as is', () => {
   expect(formatData('Test string')).toBe('Test string');
 });
 
 test('formats JSON string', () => {
   const jsonString = '{"key":"value"}';
   expect(formatData(jsonString)).toBe('{\n  "key": "value"\n}');
 });
 
 test('handles stdout and stderr', () => {
   const data = { stdout: 'Output', stderr: 'Error' };
   expect(formatData(data)).toBe('Output\nError');
 });
 
 test('returns stringified data for objects', () => {
   const data = { key: 'value' };
   expect(formatData(data)).toBe('{\n  "key": "value"\n}');
 });