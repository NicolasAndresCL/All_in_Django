## Que cambia

<!-- Una frase. Si no cabe en una, probablemente sean dos PR. -->

## Por que

<!-- El problema que resuelve, no la implementacion. -->

## Como se verifico

<!-- Lo que se ejecuto de verdad, con su resultado. "Deberia funcionar" no cuenta. -->

- [ ] `scripts\verificar.ps1` en verde (lint + tests + cobertura + hardening)
- [ ] Si toca Docker/compose: el stack levanta y los tres servicios quedan `healthy`
- [ ] Si toca la base: hay un respaldo previo (`scripts\respaldar_bd.ps1`)
- [ ] Documentacion actualizada (README / CLAUDE.md) si el cambio la deja obsoleta
