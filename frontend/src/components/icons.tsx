import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function base(props: IconProps) {
  return {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.4,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    focusable: false,
    ...props,
  }
}

export function FolderMark(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3.25 7.25h5.1l1.55 2.1h10.85v9.4H3.25z" />
      <path d="M3.25 7.25v-2h5.1l1.55 2" />
      <path d="M6.6 12h10.8" strokeOpacity=".55" />
    </svg>
  )
}

export function SunIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="3.4" />
      <path d="M12 2.8v2.1M12 19.1v2.1M2.8 12h2.1M19.1 12h2.1M5.5 5.5l1.5 1.5M17 17l1.5 1.5M18.5 5.5L17 7M7 17l-1.5 1.5" />
    </svg>
  )
}

export function MoonIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M19.4 14.6A7.6 7.6 0 0 1 9.4 4.6a7.6 7.6 0 1 0 10 10Z" />
    </svg>
  )
}

export function UploadIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 16V4.8M7.6 9.2 12 4.8l4.4 4.4" />
      <path d="M4.2 14.6v4.6h15.6v-4.6" />
    </svg>
  )
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M19 12H5M10.4 6.6 5 12l5.4 5.4" />
    </svg>
  )
}

export function ExternalIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M13.8 5.2H19v5.2M19 5.2l-7.4 7.4" />
      <path d="M17 14.2v4.6H5.2V7h4.6" />
    </svg>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="10.8" cy="10.8" r="5.8" />
      <path d="m15.1 15.1 4.3 4.3" />
    </svg>
  )
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m7 9.5 5 5 5-5" />
    </svg>
  )
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />
    </svg>
  )
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m5.2 12.4 4.3 4.2 9.3-9.2" />
    </svg>
  )
}

export function FileIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6.2 3.8h7.4l4.2 4.2v12.2H6.2z" />
      <path d="M13.6 3.8V8h4.2M9 12h6M9 15.2h6" />
    </svg>
  )
}
