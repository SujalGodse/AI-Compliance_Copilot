// Centralized API configuration for React frontend
export const API_BASE = (window.location.hostname === '15.207.88.50.nip.io' || window.location.hostname === 'localhost')
  ? '/api'
  : 'https://15.207.88.50.nip.io/api';
