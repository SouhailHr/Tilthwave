/**
 * The mark drawn for dark surfaces (the reverse lockup's mark without its tile): sage bottom
 * furrow, green middle, shoot top and leaf, amber signal. Inline so it paints with the first
 * HTML on the sign-in screen, where it sits on the canvas.
 */
export function BrandMarkOnDark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" className={className} role="img" aria-label="tilthwave">
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="9.5">
        <path d="M14 100 C 27.3 93, 39.7 93, 53 100 S 78.7 107, 92 100" stroke="#EEF2E4" />
        <path d="M14 80 C 26.6 73, 38.4 73, 51 80 S 75.4 87, 88 80" stroke="#4F9A4A" />
        <path d="M14 60 C 26.6 53, 38.4 53, 51 60 S 70 66, 76 56 C 80 49, 81 42, 79 34" stroke="#8CCB5E" />
      </g>
      <path d="M75.5 34 C 75 18, 90 4, 111 6 C 111 23, 97 37, 75.5 34 Z" fill="#8CCB5E" />
      <path
        d="M79 31 C 87 24, 96 17, 105 11.5"
        stroke="#1E2A1C"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        opacity=".55"
      />
      <circle cx="101" cy="80" r="6.2" fill="#E3A33B" />
    </svg>
  );
}
