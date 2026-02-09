import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

export function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function throttle(func, limit) {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

export function interpolateColor(color1, color2, factor) {
  const hex1 = color1.replace('#', '');
  const hex2 = color2.replace('#', '');
  
  const r1 = parseInt(hex1.substring(0, 2), 16);
  const g1 = parseInt(hex1.substring(2, 4), 16);
  const b1 = parseInt(hex1.substring(4, 6), 16);
  
  const r2 = parseInt(hex2.substring(0, 2), 16);
  const g2 = parseInt(hex2.substring(2, 4), 16);
  const b2 = parseInt(hex2.substring(4, 6), 16);
  
  const r = Math.round(r1 + (r2 - r1) * factor);
  const g = Math.round(g1 + (g2 - g1) * factor);
  const b = Math.round(b1 + (b2 - b1) * factor);
  
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

export function getTextShadowCSS(shadow) {
  switch (shadow) {
    case 'light':
      return '0 1px 2px rgba(0,0,0,0.5)';
    case 'medium':
      return '0 2px 4px rgba(0,0,0,0.6), 0 4px 8px rgba(0,0,0,0.4)';
    case 'heavy':
      return '0 0 0 4px rgba(0,0,0,0.8), 0 4px 12px rgba(0,0,0,0.8), 0 8px 24px rgba(0,0,0,0.6)';
    default:
      return 'none';
  }
}

export function getAnimationCSS(animation) {
  switch (animation) {
    case 'pop':
      return 'animate-pop-in';
    case 'slide-up':
      return 'animate-slide-up';
    case 'fade':
      return 'animate-fade-in';
    case 'bounce':
      return 'animate-bounce-in';
    default:
      return '';
  }
}
