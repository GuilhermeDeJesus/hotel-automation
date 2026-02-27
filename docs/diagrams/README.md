# Diagramas da Arquitetura

Esta pasta contém os diagramas em formato Mermaid (`.mmd`) para exportar em SVG/PNG.

## Arquivos

- `01-layer-map.mmd`
- `02-e2e-webhook-sequence.mmd`
- `03-ai-conversation-flow.mmd`
- `04-checkin-flow.mmd`
- `05-reservation-confirmation-state.mmd`
- `06-confirmation-tracing-sequence.mmd`
- `07-ai-tracing-sequence.mmd`

## Como visualizar no VS Code

1. Abra qualquer arquivo `.mmd`.
2. Use `Open Preview` no editor.

## Como exportar para SVG/PNG com Docker (sem Node local)

No PowerShell, execute na raiz do projeto:

```powershell
docker run --rm -v "${PWD}:/data" minlag/mermaid-cli -i /data/docs/diagrams/01-layer-map.mmd -o /data/docs/diagrams/01-layer-map.svg
```

Troque o arquivo de entrada/saída para os demais diagramas.

## Como exportar todos com Mermaid CLI (quando tiver Node/npm)

```powershell
mmdc -i docs/diagrams/01-layer-map.mmd -o docs/diagrams/01-layer-map.svg
mmdc -i docs/diagrams/02-e2e-webhook-sequence.mmd -o docs/diagrams/02-e2e-webhook-sequence.svg
mmdc -i docs/diagrams/03-ai-conversation-flow.mmd -o docs/diagrams/03-ai-conversation-flow.svg
mmdc -i docs/diagrams/04-checkin-flow.mmd -o docs/diagrams/04-checkin-flow.svg
mmdc -i docs/diagrams/05-reservation-confirmation-state.mmd -o docs/diagrams/05-reservation-confirmation-state.svg
mmdc -i docs/diagrams/06-confirmation-tracing-sequence.mmd -o docs/diagrams/06-confirmation-tracing-sequence.svg
mmdc -i docs/diagrams/07-ai-tracing-sequence.mmd -o docs/diagrams/07-ai-tracing-sequence.svg
```
