---
name: System Architecture Documentation
about: Dokument og tegn systemarkitekturen for FireGuard-tjenesten
title: 'Tegn og dokumenter systemarkitektur'
labels: documentation, architecture
assignees: ''
---

## Beskrivelse

Vi trenger å tegne og dokumentere systemarkitekturen for FireGuard-tjenesten for å gi et tydelig overblikk over hvordan de forskjellige komponentene i systemet henger sammen.

## Krav til dokumentasjon

Arkitekturen må vise følgende komponenter og dataflyt:

1. **MET API** (Meteorologisk institutt sitt API)
   - Datakilde for værdata (temperatur, luftfuktighet, vindstyrke)
   - Ekstern integrasjon

2. **FireGuard-tjeneste** (vår hovedapplikasjon)
   - Mottar og behandler værdata fra MET API
   - Beregner brannrisiko ved hjelp av FRCM-modellen (Fire Risk Calculation Model)
   - Database for lagring av værdata og brannrisiko-prediksjoner
   - REST API for sluttbrukere

3. **Database**
   - Lagrer historiske værdata
   - Lagrer beregnede brannrisiko-indikatorer
   - Type database (PostgreSQL, MongoDB, etc.)

4. **Meldingskø** (Message Queue)
   - Asynkron kommunikasjon
   - Type (RabbitMQ, Apache Kafka, Azure Service Bus, etc.)
   - Brukes til å distribuere risikovarsler

5. **REST API Endepunkter**
   - Sluttbrukerens tilgang til systemet
   - Endepunkter for å hente brannrisiko
   - Endepunkter for historiske data

## Ønskede diagrammer

1. **Systemarkitektur-diagram**: Viser alle komponenter og deres relasjoner
2. **Dataflyt-diagram**: Viser hvordan data flyter fra MET API til sluttbrukeren
3. **Sekvensdiagram** (valgfritt): Viser typiske API-kall-sekvenser

## Dokumentasjonsformat

- Diagrammer kan lages med:
  - Mermaid (for inline markdown-diagrammer)
  - PlantUML
  - Draw.io / Lucidchart
  - Eller annet foretrukket verktøy

- Dokumentasjonen skal legges i `docs/architecture.md`
- Diagrammer kan legges i `docs/diagrams/` (hvis eksterne filer brukes)

## Forventet resultat

Etter at denne oppgaven er fullført, skal vi ha:

- [ ] En `docs/architecture.md` fil med fullstendig arkitekturbeskrivelse
- [ ] Systemarkitektur-diagram som viser alle hovedkomponenter
- [ ] Dataflyt-diagram som viser flyt fra MET API → FireGuard → Database → Meldingskø → REST API
- [ ] Beskrivelser av hver komponent og deres ansvar
- [ ] Teknologivalg (eller forslag) for hver komponent
- [ ] Oppdatert README.md med lenke til arkitekturdokumentasjonen

## Ytterligere detaljer

- Fokuser på høynivå arkitektur først
- Inkluder hvilke datapunkter som flyter mellom komponentene
- Beskriv hvordan brannrisiko-beregningen (FRCM) integreres i det større systemet
- Dokumenter hvordan systemet skalerer og håndterer feil

## Referanser

- Eksisterende README: Beskriver FRCM-modellen (Fire Risk Calculation Model)
- Publisert paper: https://doi.org/10.1016/j.procs.2024.05.195
- MET API dokumentasjon: https://api.met.no/
