/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Primary brand colors (a deep purple for a premium feel)
        primary: {
          DEFAULT: '#6D28D9',
          light: '#8B5CF6',
          dark: '#5B21B6',
        },
        // Secondary accent color (for highlights, etc.)
        secondary: {
          DEFAULT: '#EC4899', // A vibrant pink
          light: '#F472B6',
          dark: '#DB2777',
        },
        // Neutral colors for text, backgrounds, borders (dark theme oriented)
        dark: {
          DEFAULT: '#111827', // Very dark background
          light: '#1F2937', // Slightly lighter dark for elements
          lighter: '#374151', // Even lighter dark for borders/accents
          text: '#D1D5DB', // Light gray for text on dark backgrounds
          'text-light': '#E5E7EB', // Lighter gray for secondary text
        },
        // Light theme colors (if needed, currently dark-centric)
        light: {
          DEFAULT: '#F9FAFB', // Light background
          dark: '#E5E7EB', // Slightly darker light for elements
          text: '#374151', // Dark gray for text on light backgrounds
        },
        // Status colors
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        info: '#3B82F6',
      },
      fontFamily: {
        sans: ['Inter', 'Poppins', 'sans-serif'], // Default sans-serif, good for UI
        heading: ['Bebas Neue', 'Oswald', 'sans-serif'], // For impactful headings
        mono: ['monospace'], // For code/mono text
      },
      // Extend spacing for more granular control
      spacing: {
        '18': '4.5rem',
        '112': '28rem',
        '120': '30rem',
      },
      // Extend border-radius for softer corners
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
