# Engram Sync — Memoria compartida del equipo

Este directorio contiene chunks de memoria comprimidos generados por `engram sync`.
**No editar manualmente.** Sí versionar en git.

## Para importar la memoria en tu máquina

```bash
# Desde la raíz del repo, una sola vez (y cada vez que hagas git pull):
engram sync --import
```

## Para exportar tus nuevas memorias al equipo

```bash
engram sync --project active-trace-nla
git add .engram/
git commit -m "chore(engram): sync team memories"
git push
```

## Convención

- Exportar solo con `--project active-trace-nla` para no filtrar otros proyectos.
- Scope `personal` = no se comparte. Scope `project` = va al chunk.
- Hacer sync + commit después de cada `/opsx:archive`.
