import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  activeFilterCount,
  EMPTY_FILTERS,
  type FilterState,
} from '../lib/filters'
import { FilterPanel } from './FilterPanel'

function Harness({
  onChange,
  onClear,
}: {
  onChange: (filters: FilterState) => void
  onClear?: () => void
}) {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  return (
    <FilterPanel
      idPrefix="rail"
      filters={filters}
      onChange={(next) => {
        setFilters(next)
        onChange(next)
      }}
      onClear={() => {
        setFilters(EMPTY_FILTERS)
        onClear?.()
      }}
      activeCount={activeFilterCount(filters)}
    />
  )
}

describe('FilterPanel', () => {
  it('reports a complete role value while typing', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)

    await userEvent.type(screen.getByLabelText('Role'), 'AI')

    expect(onChange).toHaveBeenLastCalledWith({
      ...EMPTY_FILTERS,
      role: 'AI',
    })
  })

  it('shows a clear control only when filters are active', async () => {
    const onClear = vi.fn()
    render(<Harness onChange={vi.fn()} onClear={onClear} />)

    expect(
      screen.queryByRole('button', { name: /clear filters/i }),
    ).toBeNull()

    await userEvent.click(screen.getByLabelText('Remote only'))

    expect(
      screen.getByRole('button', { name: /clear filters/i }),
    ).toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: /clear filters/i }),
    )
    expect(onClear).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('Remote only')).not.toBeChecked()
  })
})
