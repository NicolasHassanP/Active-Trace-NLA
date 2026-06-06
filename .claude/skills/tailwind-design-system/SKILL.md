---
name: tailwind-design-system
description: >
  Sistema de diseño con Tailwind CSS v4 para food-store.
  Usar siempre que se trabaje con animaciones CSS, dark mode, custom utilities,
  container queries, colores OKLCH, migración de v3 a v4, o cualquier patrón
  avanzado de Tailwind. También activar ante preguntas sobre @theme, @utility,
  @keyframes, ThemeProvider, o cómo hacer transiciones y efectos visuales.
  Para patrones avanzados leer references/advanced-patterns.md.
---

# Tailwind Design System — Food Store

Sistema de diseño basado en Tailwind CSS v4. Este skill cubre los patrones
de configuración y uso de Tailwind en el proyecto.

---

## Principios del sistema

- **CSS-first**: la configuración vive en bloques `@theme` dentro del CSS, no en `tailwind.config.ts`
- **Colores OKLCH**: mejor uniformidad perceptual que HSL
- **Tokens semánticos**: usar `bg-primary` en lugar de `bg-blue-500`
- **Dark mode nativo**: via `@custom-variant dark` + clase en el `<html>`
- **Sin `forwardRef`**: React 19 pasa `ref` como prop directamente

---

## Configuración base (`@theme`)

```css
@import "tailwindcss";

@theme {
  /* Colores semánticos */
  --color-primary: oklch(45% 0.2 260);
  --color-secondary: oklch(65% 0.15 200);
  --color-danger: oklch(55% 0.22 25);
  --color-success: oklch(60% 0.18 145);

  /* Variantes con alpha */
  --color-primary-10: color-mix(in oklab, var(--color-primary) 10%, transparent);
  --color-primary-20: color-mix(in oklab, var(--color-primary) 20%, transparent);

  /* Tipografía */
  --font-sans: var(--font-inter), system-ui, sans-serif;

  /* Containers */
  --container-xs: 20rem;
  --container-sm: 24rem;
}

@custom-variant dark (&:where(.dark, .dark *));
```

---

## Dark mode

```tsx
// Agregar/quitar clase 'dark' en <html>
document.documentElement.classList.toggle('dark', isDark)

// Usar en componentes
<div className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100">
```

---

## Custom utilities (`@utility`)

```css
/* Línea decorativa superior */
@utility line-t {
  @apply relative before:absolute before:top-0 before:-left-[100vw]
         before:h-px before:w-[200vw] before:bg-gray-950/5
         dark:before:bg-white/10;
}

/* Texto con gradiente */
@utility text-gradient {
  @apply bg-gradient-to-r from-primary to-secondary
         bg-clip-text text-transparent;
}
```

---

## Clases condicionales con `clsx`

```tsx
import clsx from 'clsx'

<button className={clsx(
  'px-4 py-2 rounded-lg font-medium transition-colors',
  isPending && 'opacity-50 cursor-not-allowed',
  variant === 'primary'
    ? 'bg-[--color-primary] text-white hover:bg-[--color-primary-80]'
    : 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100'
)}>
```

---

## Checklist v3 → v4

- [ ] Reemplazar `tailwind.config.ts` con bloque `@theme` en CSS
- [ ] Cambiar `@tailwind base/components/utilities` por `@import "tailwindcss"`
- [ ] Mover colores a `@theme { --color-*: value }`
- [ ] Reemplazar `darkMode: "class"` por `@custom-variant dark`
- [ ] Mover `@keyframes` dentro de bloques `@theme`
- [ ] Reemplazar `require("tailwindcss-animate")` por animaciones CSS nativas
- [ ] Actualizar `h-10 w-10` a `size-10`
- [ ] Eliminar `forwardRef` (React 19 pasa ref como prop)
- [ ] Migrar a colores OKLCH
- [ ] Reemplazar plugins custom por directivas `@utility`

---

## Referencia de patrones avanzados

Para animaciones nativas, dark mode con ThemeProvider completo, namespace
overrides y más ejemplos detallados, leer:

→ `references/advanced-patterns.md`
