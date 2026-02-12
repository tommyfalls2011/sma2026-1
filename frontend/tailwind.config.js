/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fef3e2',
          100: '#fde4b8',
          200: '#fcd48a',
          300: '#fbc45c',
          400: '#fab838',
          500: '#f9a825',
          600: '#f59100',
          700: '#e07c00',
          800: '#c96800',
          900: '#a85200',
        },
        dark: {
          50: '#f5f5f5',
          100: '#e0e0e0',
          200: '#bdbdbd',
          300: '#9e9e9e',
          400: '#757575',
          500: '#616161',
          600: '#424242',
          700: '#303030',
          800: '#212121',
          900: '#121212',
          950: '#0a0a0a',
        }
      },
      fontFamily: {
        display: ['Oswald', 'sans-serif'],
        body: ['Barlow', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
