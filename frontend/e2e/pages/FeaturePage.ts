import { expect, type Page } from '@playwright/test'

/**
 * Generic feature page object. Most activia-trace feature pages render a
 * `PageHeader` (h1) plus their own content. This base navigates by URL and
 * asserts the header + absence of the React error / 404 fallbacks.
 */
export class FeaturePage {
  constructor(
    protected readonly page: Page,
    private readonly route: string,
    private readonly title: string,
  ) {}

  async goto(): Promise<void> {
    await this.page.goto(this.route)
  }

  /** Assert the page rendered its header and is not a 404 / blank crash. */
  async expectLoaded(): Promise<void> {
    await expect(this.page.getByRole('heading', { level: 1, name: this.title })).toBeVisible({
      timeout: 15_000,
    })
    // Must NOT be the NotFound404 screen.
    await expect(this.page.getByRole('heading', { name: '404' })).toHaveCount(0)
  }
}

/** Padrón page (/padron). */
export class PadronPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/padron', 'Importación de Padrón')
  }
}

/** Calificaciones page (/calificaciones). */
export class CalificacionesPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/calificaciones', 'Calificaciones')
  }
}

/** Atrasados page (/atrasados). */
export class AtrasadosPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/atrasados', 'Alumnos atrasados')
  }
}

/** Comunicaciones page (/comunicaciones). */
export class ComunicacionesPage extends FeaturePage {
  constructor(private readonly p: Page) {
    super(p, '/comunicaciones', 'Comunicaciones')
  }

  tab(testid: 'componer' | 'historial' | 'pendientes') {
    return this.p.getByTestId(`tab-${testid}`)
  }
}

/** Equipos docentes page (/equipos). */
export class EquiposPage extends FeaturePage {
  constructor(private readonly p: Page) {
    super(p, '/equipos', 'Equipos docentes')
  }

  gestionPanel() {
    return this.p.getByTestId('equipos-gestion')
  }
}

/** Avisos page (/avisos). */
export class AvisosPage extends FeaturePage {
  constructor(private readonly p: Page) {
    super(p, '/avisos', 'Avisos')
  }

  gestionPanel() {
    return this.p.getByTestId('avisos-gestion')
  }

  bandeja() {
    return this.p.getByTestId('avisos-bandeja')
  }
}

/** Tareas page (/tareas). */
export class TareasPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/tareas', 'Tareas')
  }
}

/** Monitor page (/monitor). */
export class MonitorPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/monitor', 'Monitor general de actividades')
  }
}

/** Coloquios page (/coloquios). */
export class ColoquiosPage extends FeaturePage {
  constructor(private readonly p: Page) {
    super(p, '/coloquios', 'Coloquios')
  }

  panel() {
    return this.p.getByTestId('coloquios-panel')
  }

  accessDenied() {
    return this.p.getByTestId('coloquios-access-denied')
  }
}

/** Mi cursada page (/mi-cursada) — ALUMNO. */
export class MiCursadaPage extends FeaturePage {
  constructor(private readonly p: Page) {
    super(p, '/mi-cursada', 'Mi cursada')
  }

  materiasHeading() {
    return this.p.getByRole('heading', { name: 'Materias cursadas' })
  }

  coloquiosHeading() {
    return this.p.getByRole('heading', { name: 'Coloquios reservados' })
  }
}

/** Mis coloquios page (/mis-coloquios) — ALUMNO reserva. */
export class MisColoquiosPage extends FeaturePage {
  constructor(page: Page) {
    super(page, '/mis-coloquios', 'Mis coloquios')
  }
}
