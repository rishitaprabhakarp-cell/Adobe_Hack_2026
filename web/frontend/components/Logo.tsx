export default function Logo({
  dark = false,
  size = 28,
}: {
  dark?: boolean;
  size?: number;
}) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 28 28"
        fill="none"
        aria-hidden="true"
      >
        <rect
          width="28"
          height="28"
          rx="7"
          fill={dark ? "#111111" : "#4F46E5"}
        />
        <path
          d="M8.5 15.2L14 8.5l5.5 6.7"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M10.2 16.8L14 12.4l3.8 4.4"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.7"
        />
      </svg>
      <span
        className={`text-[15px] font-semibold tracking-tight ${
          dark ? "text-neutral-900" : "text-white"
        }`}
      >
        GEOReady
      </span>
    </span>
  );
}
