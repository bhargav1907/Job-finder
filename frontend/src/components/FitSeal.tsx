import { formatScore } from '../lib/format'

interface FitSealProps {
  score: number
  size?: 'sm' | 'lg'
}

export function FitSeal({ score, size = 'lg' }: FitSealProps) {
  const rounded = formatScore(score)

  return (
    <div
      role="img"
      aria-label={`Fit score ${rounded} out of 100`}
      className={`fit-seal ${size === 'sm' ? 'fit-seal-sm' : 'fit-seal-lg'}`}
    >
      <span className="fit-seal-score" aria-hidden="true">
        {rounded}
      </span>
      <span className="fit-seal-label" aria-hidden="true">
        fit
      </span>
    </div>
  )
}
