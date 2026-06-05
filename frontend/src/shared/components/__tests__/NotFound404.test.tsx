/**
 * Tests for NotFound404 and Forbidden403 screens — task 9.4
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import NotFound404 from '../NotFound404'
import Forbidden403 from '../Forbidden403'

describe('NotFound404', () => {
  it('renders 404 message', () => {
    render(
      <MemoryRouter>
        <NotFound404 />
      </MemoryRouter>,
    )
    expect(screen.getByText('404')).toBeInTheDocument()
    expect(screen.getByText(/página no encontrada/i)).toBeInTheDocument()
  })

  it('shows 404 for unknown routes', () => {
    render(
      <MemoryRouter initialEntries={['/this/does/not/exist']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="*" element={<NotFound404 />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('404')).toBeInTheDocument()
  })
})

describe('Forbidden403', () => {
  it('renders 403 message', () => {
    render(
      <MemoryRouter>
        <Forbidden403 />
      </MemoryRouter>,
    )
    expect(screen.getByText('403')).toBeInTheDocument()
    expect(screen.getByText(/acceso denegado/i)).toBeInTheDocument()
  })
})
